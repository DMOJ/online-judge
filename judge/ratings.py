from itertools import izip
import math
from operator import itemgetter
from django.db import connection, transaction
from django.utils import timezone
from judge.models import Rating


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
    if N == 1:
        return new_rating, new_volatility

    ranking = range(N)
    ranking.sort(key=old_rating.__getitem__, reverse=True)

    ave_rating = float(sum(old_rating)) / N
    sum1 = sum(i * i for i in old_volatility) / N
    sum2 = sum((i - ave_rating) ** 2 for i in old_rating) / (N - 1)
    CF = math.sqrt(sum1 + sum2)

    for i in xrange(N):
        ERank = 0.5
        for j in xrange(N):
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

        new_volatility[i] = math.sqrt(((new_rating[i] - old_rating[i]) ** 2) / Weight + (old_volatility[i] ** 2) / (Weight + 1))
        new_rating[i] = (old_rating[i] + Weight * PerfAs) / (1.0 + Weight)
        if abs(old_rating[i] - new_rating[i]) > Cap:
            if old_rating[i] < new_rating[i]:
                new_rating[i] = old_rating[i] + Cap
            else:
                new_rating[i] = old_rating[i] - Cap

    adjust = float(sum(old_rating) - sum(new_rating)) / N
    new_rating = map(adjust.__add__, new_rating)
    return map(int, map(round, new_rating)), map(int, map(round, new_volatility))


def rate_contest(contest):
    cursor = connection.cursor()
    cursor.execute('''
        SELECT judge_rating.user_id, judge_rating.rating, judge_rating.volatility, r.times
        FROM judge_rating INNER JOIN (
            SELECT judge_rating.user_id AS id, MAX(judge_rating.last_rated) AS last_time,
                   COUNT(judge_rating.user_id) AS times
            FROM judge_contestparticipation INNER JOIN
                 judge_contestprofile ON (judge_contestparticipation.profile_id = judge_contestprofile.id) INNER JOIN
                 judge_rating ON (judge_rating.user_id = judge_contestprofile.user_id)
            WHERE judge_contestparticipation.contest_id = %s AND judge_rating.last_rated < %s
            GROUP BY judge_rating.user_id
            ORDER BY judge_contestparticipation.score DESC, judge_contestparticipation.cumtime ASC
        ) AS r ON (judge_rating.user_id = r.id AND judge_rating.last_rated = r.last_time)
    ''', (contest.id, contest.end_time))
    data = {user: (rating, volatility, times) for user, rating, volatility, times in cursor.fetchall()}
    cursor.close()

    user_ids = contest.users.order_by('-score', 'cumtime').values_list('profile__user_id', flat=True)
    old_data = [data.get(user, (1200, 535)) for user in user_ids]
    old_rating = map(itemgetter(0), old_data)
    old_volatility = map(itemgetter(1), old_data)
    times_ranked = map(itemgetter(1), old_data)
    rating, volatility = recalculate_ratings(old_rating, old_volatility, range(1, len(user_ids) + 1), times_ranked)

    now = timezone.now()
    with transaction.atomic():
        Rating.objects.filter(contest=contest).delete()
        ratings = [Rating(user_id=id, contest=contest, rating=r, volatility=v, last_rated=now)
                   for id, r, v in izip(user_ids, rating, volatility)]
        Rating.objects.bulk_create(ratings)
