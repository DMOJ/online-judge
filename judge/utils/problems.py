from django.core.cache import cache
from django.db.models import F
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