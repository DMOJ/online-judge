from collections import defaultdict
from math import e

from django.core.cache import cache
from django.db.models import Case, Count, ExpressionWrapper, F, Max, When
from django.db.models.fields import FloatField
from django.utils import timezone
from django.utils.translation import gettext as _, gettext_noop

from judge.models import Problem, Submission

__all__ = ['contest_completed_ids', 'get_result_data', 'user_completed_ids', 'user_editable_ids', 'user_tester_ids']


def user_tester_ids(profile):
    return set(Problem.objects.filter(testers=profile).values_list('id', flat=True))


def user_editable_ids(profile):
    return set(Problem.get_editable_problems(profile.user).values_list('id', flat=True))


def contest_completed_ids(participation):
    key = 'contest_complete:%d' % participation.id
    result = cache.get(key)
    if result is None:
        result = set(participation.submissions.filter(submission__result='AC', points=F('problem__points'))
                     .values_list('problem__problem__id', flat=True).distinct())
        cache.set(key, result, 86400)
    return result


def user_completed_ids(profile):
    key = 'user_complete:%d' % profile.id
    result = cache.get(key)
    if result is None:
        result = set(Submission.objects.filter(user=profile, result='AC', points=F('problem__points'))
                     .values_list('problem_id', flat=True).distinct())
        cache.set(key, result, 86400)
    return result


def contest_attempted_ids(participation):
    key = 'contest_attempted:%s' % participation.id
    result = cache.get(key)
    if result is None:
        result = {id: {'achieved_points': points, 'max_points': max_points}
                  for id, max_points, points in (participation.submissions
                                                 .values_list('problem__problem__id', 'problem__points')
                                                 .annotate(points=Max('points'))
                                                 .filter(points__lt=F('problem__points')))}
        cache.set(key, result, 86400)
    return result


def user_attempted_ids(profile):
    key = 'user_attempted:%s' % profile.id
    result = cache.get(key)
    if result is None:
        result = {id: {'achieved_points': points, 'max_points': max_points}
                  for id, max_points, points in (Submission.objects.filter(user=profile)
                                                 .values_list('problem__id', 'problem__points')
                                                 .annotate(points=Max('points'))
                                                 .filter(points__lt=F('problem__points')))}
        cache.set(key, result, 86400)
    return result


def _get_result_data(results):
    return {
        'categories': [
            # Using gettext_noop here since this will be tacked into the cache, so it must be language neutral.
            # The caller, SubmissionList.get_result_data will run ugettext on the name.
            {'code': 'AC', 'name': gettext_noop('Accepted'), 'count': results['AC']},
            {'code': 'WA', 'name': gettext_noop('Wrong'), 'count': results['WA']},
            {'code': 'CE', 'name': gettext_noop('Compile Error'), 'count': results['CE']},
            {'code': 'TLE', 'name': gettext_noop('Timeout'), 'count': results['TLE']},
            {'code': 'ERR', 'name': gettext_noop('Error'),
             'count': results['MLE'] + results['OLE'] + results['IR'] + results['RTE'] + results['AB'] + results['IE']},
        ],
        'total': sum(results.values()),
    }


def get_result_data(*args, **kwargs):
    if args:
        submissions = args[0]
        if kwargs:
            raise ValueError(_("Can't pass both queryset and keyword filters"))
    else:
        submissions = Submission.objects.filter(**kwargs) if kwargs is not None else Submission.objects
    raw = submissions.values('result').annotate(count=Count('result')).values_list('result', 'count')
    return _get_result_data(defaultdict(int, raw))


def hot_problems(duration, limit):
    cache_key = 'hot_problems:%d:%d' % (duration.total_seconds(), limit)
    qs = cache.get(cache_key)
    if qs is None:
        qs = Problem.get_public_problems() \
                    .filter(submission__date__gt=timezone.now() - duration, points__gt=3, points__lt=25)
        qs0 = qs.annotate(k=Count('submission__user', distinct=True)).order_by('-k').values_list('k', flat=True)

        if not qs0:
            return []
        # make this an aggregate
        mx = float(qs0[0])

        qs = qs.annotate(unique_user_count=Count('submission__user', distinct=True))
        # fix braindamage in excluding CE
        qs = qs.annotate(submission_volume=Count(Case(
            When(submission__result='AC', then=1),
            When(submission__result='WA', then=1),
            When(submission__result='IR', then=1),
            When(submission__result='RTE', then=1),
            When(submission__result='TLE', then=1),
            When(submission__result='OLE', then=1),
            output_field=FloatField(),
        )))
        qs = qs.annotate(ac_volume=Count(Case(
            When(submission__result='AC', then=1),
            output_field=FloatField(),
        )))
        qs = qs.filter(unique_user_count__gt=max(mx / 3.0, 1))

        qs = qs.annotate(ordering=ExpressionWrapper(
            0.5 * F('points') * (0.4 * F('ac_volume') / F('submission_volume') + 0.6 * F('ac_rate')) +
            100 * e ** (F('unique_user_count') / mx), output_field=FloatField(),
        )).order_by('-ordering').defer('description')[:limit]

        cache.set(cache_key, qs, 900)
    return qs
