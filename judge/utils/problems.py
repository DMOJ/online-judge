from django.db.models import F
from judge.models import Submission

__all__ = ['contest_completed_ids', 'user_completed_ids']


def contest_completed_ids(participation):
    return set(participation.submissions.filter(submission__result='AC', points=F('problem__points'))
                            .values_list('problem__problem__id', flat=True).distinct())


def user_completed_ids(profile):
    return set(Submission.objects.filter(user=profile, result='AC', points=F('problem__points'))
               .values_list('problem_id', flat=True).distinct())