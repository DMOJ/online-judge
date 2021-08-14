import math
from operator import attrgetter, itemgetter

from django.db import migrations, models
from django.db.models import Count, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone


def tie_ranker(iterable, key=attrgetter('points')):
    rank = 0
    delta = 1
    last = None
    buf = []
    for item in iterable:
        new = key(item)
        if new != last:
            for _ in buf:
                yield rank + (delta - 1) / 2.0
            rank += delta
            delta = 0
            buf = []
        delta += 1
        buf.append(item)
        last = key(item)
    for _ in buf:
        yield rank + (delta - 1) / 2.0


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


def recalculate_ratings(old_rating, old_volatility, actual_rank, times_rated, is_disqualified):
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

        if abs(old_rating[i] - new_rating[i]) > Cap:
            if old_rating[i] < new_rating[i]:
                new_rating[i] = old_rating[i] + Cap
            else:
                new_rating[i] = old_rating[i] - Cap

        if times_rated[i] == 0:
            new_volatility[i] = 385
        else:
            new_volatility[i] = math.sqrt(((new_rating[i] - old_rating[i]) ** 2) / Weight +
                                          (old_volatility[i] ** 2) / (Weight + 1))

        if is_disqualified[i]:
            # DQed users can manipulate TopCoder ratings to get higher volatility in order to increase their rating
            # later on, prohibit this by ensuring their volatility never increases in this situation
            new_volatility[i] = min(new_volatility[i], old_volatility[i])

    # try to keep the sum of ratings constant
    adjust = float(sum(old_rating) - sum(new_rating)) / N
    new_rating = list(map(adjust.__add__, new_rating))
    # inflate a little if we have to so people who placed first don't lose rating
    best_rank = min(actual_rank)
    for i in range(N):
        if abs(actual_rank[i] - best_rank) <= 1e-3 and new_rating[i] < old_rating[i] + 1:
            new_rating[i] = old_rating[i] + 1
    return list(map(int, map(round, new_rating))), list(map(int, map(round, new_volatility)))


def tc_rate_contest(contest, Rating, Profile):
    rating_subquery = Rating.objects.filter(user=OuterRef('user'))
    rating_sorted = rating_subquery.order_by('-contest__end_time')
    users = contest.users.order_by('is_disqualified', '-score', 'cumtime', 'tiebreaker') \
        .annotate(submissions=Count('submission'),
                  last_rating=Coalesce(Subquery(rating_sorted.values('rating')[:1]), 1200),
                  volatility=Coalesce(Subquery(rating_sorted.values('volatility')[:1]), 535),
                  times=Coalesce(Subquery(rating_subquery.order_by().values('user_id')
                                          .annotate(count=Count('id')).values('count')), 0)) \
        .exclude(user_id__in=contest.rate_exclude.all()) \
        .filter(virtual=0).values('id', 'user_id', 'score', 'cumtime', 'tiebreaker', 'is_disqualified',
                                  'last_rating', 'volatility', 'times')
    if not contest.rate_all:
        users = users.filter(submissions__gt=0)
    if contest.rating_floor is not None:
        users = users.exclude(last_rating__lt=contest.rating_floor)
    if contest.rating_ceiling is not None:
        users = users.exclude(last_rating__gt=contest.rating_ceiling)

    users = list(users)
    participation_ids = list(map(itemgetter('id'), users))
    user_ids = list(map(itemgetter('user_id'), users))
    is_disqualified = list(map(itemgetter('is_disqualified'), users))
    ranking = list(tie_ranker(users, key=itemgetter('score', 'cumtime', 'tiebreaker')))
    old_rating = list(map(itemgetter('last_rating'), users))
    old_volatility = list(map(itemgetter('volatility'), users))
    times_ranked = list(map(itemgetter('times'), users))
    rating, volatility = recalculate_ratings(old_rating, old_volatility, ranking, times_ranked, is_disqualified)

    now = timezone.now()
    ratings = [Rating(user_id=i, contest=contest, rating=r, volatility=v, last_rated=now, participation_id=p, rank=z)
               for i, p, r, v, z in zip(user_ids, participation_ids, rating, volatility, ranking)]

    Rating.objects.bulk_create(ratings)

    Profile.objects.filter(contest_history__contest=contest, contest_history__virtual=0).update(
        rating=Subquery(Rating.objects.filter(user=OuterRef('id'))
                        .order_by('-contest__end_time').values('rating')[:1]))


# inspired by rate_all_view
def rate_tc(apps, schema_editor):
    Contest = apps.get_model('judge', 'Contest')
    Rating = apps.get_model('judge', 'Rating')
    Profile = apps.get_model('judge', 'Profile')

    with schema_editor.connection.cursor() as cursor:
        cursor.execute('TRUNCATE TABLE `%s`' % Rating._meta.db_table)
    Profile.objects.update(rating=None)
    for contest in Contest.objects.filter(is_rated=True, end_time__lte=timezone.now()).order_by('end_time'):
        tc_rate_contest(contest, Rating, Profile)


# inspired by rate_all_view
def rate_elo_mmr(apps, schema_editor):
    Rating = apps.get_model('judge', 'Rating')
    Profile = apps.get_model('judge', 'Profile')

    with schema_editor.connection.cursor() as cursor:
        cursor.execute('TRUNCATE TABLE `%s`' % Rating._meta.db_table)
    Profile.objects.update(rating=None)
    # Don't populate Rating


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0122_username_display_override'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, rate_tc, atomic=True),
        migrations.AddField(
            model_name='rating',
            name='mean',
            field=models.FloatField(verbose_name='raw rating'),
        ),
        migrations.AddField(
            model_name='rating',
            name='performance',
            field=models.FloatField(verbose_name='contest performance'),
        ),
        migrations.RemoveField(
            model_name='rating',
            name='volatility',
            field=models.IntegerField(verbose_name='volatility'),
        ),
        migrations.RunPython(rate_elo_mmr, migrations.RunPython.noop, atomic=True),
    ]
