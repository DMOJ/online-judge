import math
from bisect import bisect
from itertools import izip
from operator import itemgetter

from django.db import connection, transaction
from django.db.models import Count
from django.utils import timezone

from judge.utils.ranker import tie_ranker


def get_elo_win_probability(rating_a, rating_b):
    # given users with ratings rating_a and rating_b, compute the probability
    # that person A achieves a higher position than rating B
    # source: https://codeforces.com/blog/entry/102
    return 1.0/(1 + (10 ** ((rating_b - rating_a) / 400.)))


def get_seed(user_rating, rating_to_ignore, ratings):
    # given a user with rating user_rating, compute their expected seed
    # source: https://codeforces.com/blog/entry/102
    ignore_rating = True
    seed = 1.0
    for opponent_rating in ratings:
        if opponent_rating == rating_to_ignore and ignore_rating:
            # the given user's rating will appear once, so we don't include it
            # the first time we see it
            ignore_rating = False
        else:
            seed += get_elo_win_probability(opponent_rating, user_rating)
    return seed


def get_average_rank(user_rating, real_rank, ratings):
    expected_rank = get_seed(user_rating, user_rating, ratings)
    return math.sqrt(real_rank * expected_rank)


def get_rating_to_rank(user_rating, real_rank, ratings):
    average_rank = get_average_rank(user_rating, real_rank, ratings)
    left = user_rating - 1000
    right = user_rating + 1000
    while right - left > 1:
        mid = (left + right) / 2
        seed = get_seed(mid, user_rating, ratings)
        if seed < average_rank:
            right = mid
        else:
            left = mid
    return left


def recalculate_ranks(initial_ranks):
    # if users M through N tie at ranking K, then they all get assigned rank
    # K + (N-M)
    old_ranking_to_new_ranking = {}
    sorted_ranks = sorted(initial_ranks)
    i = 0
    while i < len(sorted_ranks):
        first = i
        last = first
        rank = sorted_ranks[first]
        while last < len(sorted_ranks) and sorted_ranks[last] == rank:
            last += 1
        old_ranking_to_new_ranking[rank] = last
        i = last
    return [
        old_ranking_to_new_ranking[old_rank]
        for old_rank in old_ranking_to_new_ranking
    ]


def make_total_sum_nonpositive(deltas):
    # the sum of all ratings should not exceed zero to avoid rating inflation
    new_deltas = []
    total_sum = sum(deltas)
    inc = (-total_sum / len(deltas)) - 1
    return [delta + inc for delta in deltas]


def make_top_individuals_sum_nonpositive(deltas, actual_rank):
    # the sum of the top 4*sqrt(N) individuals should be adjusted to zero
    num_top_individuals = int(min(len(deltas), 4*round(math.sqrt(len(deltas)))))
    top_sum = sum([
        delta
        for i, delta in enumerate(deltas)
        if actual_rank[i] <= num_top_individuals
    ])
    inc = min(max(-top_sum / num_top_individuals, -10), 0)
    return [delta + inc for delta in deltas]


def calculate_deltas(old_ratings, actual_ranks):
    # compute rating deltas given the ratings and actual ranks
    deltas = []
    for i in range(len(old_ratings)):
        expected_rating = int(
            get_rating_to_rank(old_ratings[i], actual_ranks[i], old_ratings)
        )
        deltas.append((expected_rating - old_ratings[i]) / 2)
    deltas = make_total_sum_nonpositive(deltas)
    deltas = make_top_individuals_sum_nonpositive(deltas, actual_ranks)
    return deltas


def recalculate_ratings(old_ratings, actual_ranks):
    if len(old_ratings) <= 1:
        return old_ratings[:]
    # actual_rank: 1 is first place, N is last place
    actual_rank = recalculate_ranks(actual_ranks)
    deltas = calculate_deltas(old_ratings, actual_ranks)
    return [old_ratings[i] + deltas[i] for i in range(len(deltas))]


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
                   .exclude(user_id__in=contest.rate_exclude.all()).filter(virtual=0)\
                   .values_list('id', 'user_id', 'score', 'cumtime')
    if not contest.rate_all:
        users = users.filter(submissions__gt=0)
    users = list(tie_ranker(users, key=itemgetter(2, 3)))
    participation_ids = [user[1][0] for user in users]
    user_ids = [user[1][1] for user in users]
    ranking = map(itemgetter(0), users)

    # TODO: figure out default volatility in CF rating?
    old_data = [data.get(user, (1500, 535, 0)) for user in user_ids]

    old_rating = map(itemgetter(0), old_data)

    # note: volatility is unused but for backwards compatibility we'll silently
    # fetch and ignore it
    volatility = map(itemgetter(1), old_data)
    times_ranked = map(itemgetter(2), old_data)
    rating = recalculate_ratings(old_rating, ranking)

    now = timezone.now()
    ratings = [Rating(user_id=id, contest=contest, rating=r, volatility=v, last_rated=now, participation_id=p, rank=z)
               for id, p, r, v, z in izip(user_ids, participation_ids, rating, volatility, ranking)]
    cursor = connection.cursor()
    cursor.execute('CREATE TEMPORARY TABLE _profile_rating_update(id integer, rating integer)')
    cursor.executemany('INSERT INTO _profile_rating_update VALUES (%s, %s)', zip(user_ids, rating))
    with transaction.atomic():
        Rating.objects.filter(contest=contest).delete()
        Rating.objects.bulk_create(ratings)
        cursor.execute('''
            UPDATE `%s` p INNER JOIN `_profile_rating_update` tmp ON (p.id = tmp.id)
            SET p.rating = tmp.rating
        ''' % Profile._meta.db_table)
    cursor.execute('DROP TABLE _profile_rating_update')
    cursor.close()
    return old_rating, volatility, ranking, times_ranked, rating, volatility


RATING_LEVELS = [
    'Newbie',
    'Pupil',
    'Specialist',
    'Expert',
    'Candidate Master',
    'Master',
    'International Master',
    'Grandmaster',
    'International Grandmaster',
    'Legendary Grandmaster'
]
RATING_VALUES = [
    1200,
    1400,
    1600,
    1900,
    2100,
    2300,
    2400,
    2600,
    3000
]
RATING_CLASS = [
    'rate-newbie',
    'rate-pupil',
    'rate-specialist'
    'rate-expert',
    'rate-candidate-master',
    'rate-master',
    'rate-international-master'
    'rate-grandmaster',
    'rate-international-grandmaster',
    'rate-legendary-grandmaster'
]


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
