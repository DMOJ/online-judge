from bisect import bisect
from math import pi, sqrt, tanh
from operator import attrgetter, itemgetter

from django.db import transaction
from django.db.models import Count, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext_lazy


BETA2 = 328.33 ** 2
RATING_INIT = 1200      # Newcomer's rating when applying the rating floor/ceiling
MEAN_INIT = 1500.
VAR_INIT = 350**2 * (BETA2 / 212**2)
SD_INIT = sqrt(VAR_INIT)
VALID_RANGE = MEAN_INIT - 20 * SD_INIT, MEAN_INIT + 20 * SD_INIT
VAR_PER_CONTEST = 1219.047619 * (BETA2 / 212**2)
VAR_LIM = (sqrt(VAR_PER_CONTEST**2 + 4 * BETA2 * VAR_PER_CONTEST) - VAR_PER_CONTEST) / 2
SD_LIM = sqrt(VAR_LIM)
TANH_C = sqrt(3) / pi


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


def eval_tanhs(tanh_terms, x):
    return sum((wt / sd) * tanh((x - mu) / (2 * sd)) for mu, sd, wt in tanh_terms)


def solve(tanh_terms, y_tg, lin_factor=0, bounds=VALID_RANGE):
    L, R = bounds
    Ly, Ry = None, None
    while R - L > 2:
        x = (L + R) / 2
        y = lin_factor * x + eval_tanhs(tanh_terms, x)
        if y > y_tg:
            R, Ry = x, y
        elif y < y_tg:
            L, Ly = x, y
        else:
            return x
    # Use linear interpolation to be slightly more accurate.
    if Ly is None:
        Ly = lin_factor * L + eval_tanhs(tanh_terms, L)
    if y_tg <= Ly:
        return L
    if Ry is None:
        Ry = lin_factor * R + eval_tanhs(tanh_terms, R)
    if y_tg >= Ry:
        return R
    ratio = (y_tg - Ly) / (Ry - Ly)
    return L * (1 - ratio) + R * ratio


def get_var(times_ranked, cache=[VAR_INIT]):
    while times_ranked >= len(cache):
        next_var = 1. / (1. / (cache[-1] + VAR_PER_CONTEST) + 1. / BETA2)
        cache.append(next_var)
    return cache[times_ranked]


def recalculate_ratings(ranking, old_mean, times_ranked, historical_p):
    n = len(ranking)
    new_p = [0.] * n
    new_mean = [0.] * n

    # Note: pre-multiply delta by TANH_C to improve efficiency.
    delta = [TANH_C * sqrt(get_var(t) + VAR_PER_CONTEST + BETA2) for t in times_ranked]
    p_tanh_terms = [(m, d, 1) for m, d in zip(old_mean, delta)]

    # Calculate performance at index i.
    def solve_idx(i, bounds=VALID_RANGE):
        r = ranking[i]
        y_tg = 0
        for d, s in zip(delta, ranking):
            if s > r:       # s loses to r
                y_tg += 1. / d
            elif s < r:     # s beats r
                y_tg -= 1. / d
            # Otherwise, this is a tie that counts as half a win, as per Elo-MMR.
        new_p[i] = solve(p_tanh_terms, y_tg, bounds=bounds)

    # Fill all indices between i and j, inclusive. Use the fact that new_p is non-increasing.
    def divconq(i, j):
        if j - i > 1:
            k = (i + j) // 2
            solve_idx(k, bounds=(new_p[j], new_p[i]))
            divconq(i, k)
            divconq(k, j)

    if n < 2:
        new_p = list(old_mean)
        new_mean = list(old_mean)
    else:
        # Calculate performance.
        solve_idx(0)
        solve_idx(n - 1)
        divconq(0, n - 1)

        # Calculate mean.
        for i, r in enumerate(ranking):
            tanh_terms = []
            w_prev = 1.
            w_sum = 0.
            for j, h in enumerate([new_p[i]] + historical_p[i]):
                gamma2 = (VAR_PER_CONTEST if j > 0 else 0)
                h_var = get_var(times_ranked[i] + 1 - j)
                k = h_var / (h_var + gamma2)
                w = w_prev * k**2
                # Future optimization: If j is around 20, then w < 1e-3 and it is possible to break early.
                tanh_terms.append((h, sqrt(BETA2) * TANH_C, w))
                w_prev = w
                w_sum += w / BETA2
            w0 = 1. / get_var(times_ranked[i] + 1) - w_sum
            p0 = eval_tanhs(tanh_terms[1:], old_mean[i]) / w0 + old_mean[i]
            new_mean[i] = solve(tanh_terms, w0 * p0, lin_factor=w0)

    # Display a slightly lower rating to incentivize participation.
    # As times_ranked increases, new_rating converges to new_mean.
    new_rating = [max(1, round(m - (sqrt(get_var(t + 1)) - SD_LIM))) for m, t in zip(new_mean, times_ranked)]

    return new_rating, new_mean, new_p


def rate_contest(contest):
    from judge.models import Rating, Profile

    rating_subquery = Rating.objects.filter(user=OuterRef('user'))
    rating_sorted = rating_subquery.order_by('-contest__end_time')
    users = contest.users.order_by('is_disqualified', '-score', 'cumtime', 'tiebreaker') \
        .annotate(submissions=Count('submission'),
                  last_rating=Coalesce(Subquery(rating_sorted.values('rating')[:1]), RATING_INIT),
                  last_mean=Coalesce(Subquery(rating_sorted.values('mean')[:1]), MEAN_INIT),
                  times=Coalesce(Subquery(rating_subquery.order_by().values('user_id')
                                          .annotate(count=Count('id')).values('count')), 0)) \
        .exclude(user_id__in=contest.rate_exclude.all()) \
        .filter(virtual=0).values('id', 'user_id', 'score', 'cumtime', 'tiebreaker',
                                  'last_rating', 'last_mean', 'times')
    if not contest.rate_all:
        users = users.filter(submissions__gt=0)
    if contest.rating_floor is not None:
        users = users.exclude(last_rating__lt=contest.rating_floor)
    if contest.rating_ceiling is not None:
        users = users.exclude(last_rating__gt=contest.rating_ceiling)

    users = list(users)
    participation_ids = list(map(itemgetter('id'), users))
    user_ids = list(map(itemgetter('user_id'), users))
    ranking = list(tie_ranker(users, key=itemgetter('score', 'cumtime', 'tiebreaker')))
    old_mean = list(map(itemgetter('last_mean'), users))
    times_ranked = list(map(itemgetter('times'), users))
    historical_p = [[] for _ in users]

    user_id_to_idx = {uid: i for i, uid in enumerate(user_ids)}
    for h in Rating.objects.filter(user_id__in=user_ids) \
            .order_by('-contest__end_time') \
            .values('user_id', 'performance'):
        idx = user_id_to_idx[h['user_id']]
        historical_p[idx].append(h['performance'])

    rating, mean, performance = recalculate_ratings(ranking, old_mean, times_ranked, historical_p)

    now = timezone.now()
    ratings = [Rating(user_id=i, contest=contest, rating=r, mean=m, performance=perf,
                      last_rated=now, participation_id=pid, rank=z)
               for i, pid, r, m, perf, z in zip(user_ids, participation_ids, rating, mean, performance, ranking)]
    with transaction.atomic():
        Rating.objects.bulk_create(ratings)

        Profile.objects.filter(contest_history__contest=contest, contest_history__virtual=0).update(
            rating=Subquery(Rating.objects.filter(user=OuterRef('id'))
                            .order_by('-contest__end_time').values('rating')[:1]))


RATING_LEVELS = [
    gettext_lazy('Newbie'),
    gettext_lazy('Amateur'),
    gettext_lazy('Expert'),
    gettext_lazy('Candidate Master'),
    gettext_lazy('Master'),
    gettext_lazy('Grandmaster'),
    gettext_lazy('Target'),
]
RATING_VALUES = [1000, 1300, 1600, 1900, 2400, 3000]
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
