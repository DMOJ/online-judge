import math
from bisect import bisect
from operator import itemgetter

from django.db import connection, transaction
from django.db.models import Count
from django.utils import timezone

from judge.utils.ranker import tie_ranker


def rational_approximation(t):
    # Abramowitz and Stegun formula 26.2.23.
    # The absolute value of the error should be less than 4.5 e-4.
    c = [2.515517, 0.802853, 0.010328]
    d = [1.432788, 0.189269, 0.001308]
    numerator = (c[2] * t + c[1]) * t + c[0]
    denominator = ((d[2] * t + d[1]) * t + d[0]) * t + 1.0
    return t - numerator / denominator


def normal_CDF_inverse(p):
    assert 0.0 < p < 1

    # See article above for explanation of this section.
    if p < 0.5:
        # F^-1(p) = - G^-1(p)
        return -rational_approximation(math.sqrt(-2.0 * math.log(p)))
    else:
        # F^-1(p) = G^-1(1-p)
        return rational_approximation(math.sqrt(-2.0 * math.log(1.0 - p)))


def WP(RA, RB, VA, VB):
    return (math.erf((RB - RA) / math.sqrt(2 * (VA * VA + VB * VB))) + 1) / 2.0


def recalculate_ratings(old_rating, old_volatility, actual_rank, times_rated):
    # actual_rank: 1 is first place, N is last place
    # if there are ties, use the average of places (if places 2, 3, 4, 5 tie, use 3.5 for all of them)

    N = len(old_rating)
    new_rating = old_rating[:]
    new_volatility = old_volatility[:]
    if N <= 1:
        return new_rating, new_volatility

    ranking = list(range(N))
    ranking.sort(key=old_rating.__getitem__, reverse=True)

    ave_rating = float(sum(old_rating)) / N
    sum1 = sum(i * i for i in old_volatility) / N
    sum2 = sum((i - ave_rating) ** 2 for i in old_rating) / (N - 1)
    CF = math.sqrt(sum1 + sum2)

    for i in range(N):
        ERank = 0.5
        for j in range(N):
            ERank += WP(old_rating[i], old_rating[j], old_volatility[i], old_volatility[j])

        EPerf = -normal_CDF_inverse((ERank - 0.5) / N)
        APerf = -normal_CDF_inverse((actual_rank[i] - 0.5) / N)
        PerfAs = old_rating[i] + CF * (APerf - EPerf)
        Weight = 1.0 / (1 - (0.42 / (times_rated[i] + 1) + 0.18)) - 1.0
        if old_rating[i] > 2500:
            Weight *= 0.8
        elif old_rating[i] >= 2000:
            Weight *= 0.9

        Cap = 150.0 + 1500.0 / (times_rated[i] + 2)

        new_rating[i] = (old_rating[i] + Weight * PerfAs) / (1.0 + Weight)

        if times_rated[i] == 0:
            new_volatility[i] = 385
        else:
            new_volatility[i] = math.sqrt(((new_rating[i] - old_rating[i]) ** 2) / Weight +
                                          (old_volatility[i] ** 2) / (Weight + 1))
        if abs(old_rating[i] - new_rating[i]) > Cap:
            if old_rating[i] < new_rating[i]:
                new_rating[i] = old_rating[i] + Cap
            else:
                new_rating[i] = old_rating[i] - Cap

    # try to keep the sum of ratings constant
    adjust = float(sum(old_rating) - sum(new_rating)) / N
    new_rating = list(map(adjust.__add__, new_rating))
    # inflate a little if we have to so people who placed first don't lose rating
    best_rank = min(actual_rank)
    for i in range(N):
        if abs(actual_rank[i] - best_rank) <= 1e-3 and new_rating[i] < old_rating[i] + 1:
            new_rating[i] = old_rating[i] + 1
    return list(map(int, map(round, new_rating))), list(map(int, map(round, new_volatility)))


def rate_contest(contest):
    from judge.models import Rating, Profile

    cursor = connection.cursor()
    cursor.execute('''
        SELECT judge_rating.user_id, judge_rating.rating, judge_rating.volatility, r.times
        FROM judge_rating INNER JOIN
             judge_contest ON (judge_contest.id = judge_rating.contest_id) INNER JOIN (
            SELECT judge_rating.user_id AS id, MAX(judge_contest.end_time) AS last_time,
                   COUNT(judge_rating.user_id) AS times
            FROM judge_contestparticipation INNER JOIN
                 judge_rating ON (judge_rating.user_id = judge_contestparticipation.user_id) INNER JOIN
                 judge_contest ON (judge_contest.id = judge_rating.contest_id)
            WHERE judge_contestparticipation.contest_id = %s AND judge_contest.end_time < %s AND
                  judge_contestparticipation.user_id NOT IN (
                      SELECT profile_id FROM judge_contest_rate_exclude WHERE contest_id = %s
                  ) AND judge_contestparticipation.virtual = 0
            GROUP BY judge_rating.user_id
            ORDER BY judge_contestparticipation.score DESC, judge_contestparticipation.cumtime ASC
        ) AS r ON (judge_rating.user_id = r.id AND judge_contest.end_time = r.last_time)
    ''', (contest.id, contest.end_time, contest.id))
    data = {user: (rating, volatility, times) for user, rating, volatility, times in cursor.fetchall()}
    cursor.close()

    users = contest.users.order_by('-score', 'cumtime').annotate(submissions=Count('submission')) \
                   .exclude(user_id__in=contest.rate_exclude.all()).filter(virtual=0, user__is_unlisted=False) \
                   .values_list('id', 'user_id', 'score', 'cumtime')
    if not contest.rate_all:
        users = users.filter(submissions__gt=0)
    if contest.rating_floor is not None:
        users = users.exclude(user__rating__lt=contest.rating_floor)
    if contest.rating_ceiling is not None:
        users = users.exclude(user__rating__gt=contest.rating_ceiling)
    users = list(tie_ranker(users, key=itemgetter(2, 3)))
    participation_ids = [user[1][0] for user in users]
    user_ids = [user[1][1] for user in users]
    ranking = list(map(itemgetter(0), users))
    old_data = [data.get(user, (1200, 535, 0)) for user in user_ids]
    old_rating = list(map(itemgetter(0), old_data))
    old_volatility = list(map(itemgetter(1), old_data))
    times_ranked = list(map(itemgetter(2), old_data))
    rating, volatility = recalculate_ratings(old_rating, old_volatility, ranking, times_ranked)

    now = timezone.now()
    ratings = [Rating(user_id=id, contest=contest, rating=r, volatility=v, last_rated=now, participation_id=p, rank=z)
               for id, p, r, v, z in zip(user_ids, participation_ids, rating, volatility, ranking)]
    cursor = connection.cursor()
    cursor.execute('CREATE TEMPORARY TABLE _profile_rating_update(id integer, rating integer)')
    cursor.executemany('INSERT INTO _profile_rating_update VALUES (%s, %s)', list(zip(user_ids, rating)))
    with transaction.atomic():
        Rating.objects.filter(contest=contest).delete()
        Rating.objects.bulk_create(ratings)
        cursor.execute('''
            UPDATE `%s` p INNER JOIN `_profile_rating_update` tmp ON (p.id = tmp.id)
            SET p.rating = tmp.rating
        ''' % Profile._meta.db_table)
    cursor.execute('DROP TABLE _profile_rating_update')
    cursor.close()
    return old_rating, old_volatility, ranking, times_ranked, rating, volatility


RATING_LEVELS = ['Newbie', 'Amateur', 'Expert', 'Candidate Master', 'Master', 'Grandmaster', 'Target']
RATING_VALUES = [1000, 1200, 1500, 1800, 2200, 3000]
RATING_CLASS = ['rate-newbie', 'rate-amateur', 'rate-expert', 'rate-candidate-master',
                'rate-master', 'rate-grandmaster', 'rate-target']


def rating_level(rating):
    return bisect(RATING_VALUES, rating)


def rating_name(rating):
    return RATING_LEVELS[rating_level(rating)]


def rating_class(rating):
    return RATING_CLASS[rating_level(rating)]


def rating_progress(rating):
    level = bisect(RATING_VALUES, rating)
    if level == len(RATING_VALUES):
        return 1.0
    prev = 0 if not level else RATING_VALUES[level - 1]
    next = RATING_VALUES[level]
    return (rating - prev + 0.0) / (next - prev)
