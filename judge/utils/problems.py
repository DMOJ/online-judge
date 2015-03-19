from collections import defaultdict
from django.core.cache import cache
from django.db.models import F, Count
from judge.models import Submission

__all__ = ['contest_completed_ids', 'user_completed_ids']


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


def get_result_table(*args, **kwargs):
    if args:
        submissions = args[0]
        if kwargs:
            raise ValueError("Can't pass both queryset and keyword filters")
    else:
        submissions = Submission.objects.filter(**kwargs) if kwargs is not None else Submission.objects
    raw = submissions.values('result').annotate(count=Count('result')).values_list('result', 'count')
    results = defaultdict(int, raw)
    return [('Accepted', 'AC', results['AC']),
            ('Wrong Answer', 'WA', results['WA']),
            ('Compile Error', 'CE', results['CE']),
            ('Time Limit Exceed', 'TLE', results['TLE']),
            ('Memory Limit Exceed', 'MLE', results['MLE']),
            ('Invalid Return', 'IR', results['IR']),
            ('Total', 'TOT', sum(results.values()))]