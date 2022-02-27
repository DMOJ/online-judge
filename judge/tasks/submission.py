from celery import shared_task
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext as _

from judge.models import Problem, Profile, Submission
from judge.utils.celery import Progress

__all__ = ('apply_submission_filter', 'rejudge_problem_filter', 'rescore_problem')


def apply_submission_filter(queryset, id_range, languages, results):
    if id_range:
        start, end = id_range
        queryset = queryset.filter(id__gte=start, id__lte=end)
    if languages:
        queryset = queryset.filter(language_id__in=languages)
    if results:
        queryset = queryset.filter(result__in=results)
    queryset = queryset.exclude(locked_after__lt=timezone.now()) \
                       .exclude(status__in=Submission.IN_PROGRESS_GRADING_STATUS)
    return queryset


@shared_task(bind=True)
def rejudge_problem_filter(self, problem_id, id_range=None, languages=None, results=None, user_id=None):
    queryset = Submission.objects.filter(problem_id=problem_id)
    queryset = apply_submission_filter(queryset, id_range, languages, results)
    user = User.objects.get(id=user_id)

    rejudged = 0
    with Progress(self, queryset.count()) as p:
        for submission in queryset.iterator():
            submission.judge(rejudge=True, batch_rejudge=True, rejudge_user=user)
            rejudged += 1
            if rejudged % 10 == 0:
                p.done = rejudged
    return rejudged


@shared_task(bind=True)
def rescore_problem(self, problem_id):
    problem = Problem.objects.get(id=problem_id)
    submissions = Submission.objects.filter(problem_id=problem_id)

    with Progress(self, submissions.count(), stage=_('Modifying submissions')) as p:
        rescored = 0
        for submission in submissions.iterator():
            submission.points = round(submission.case_points / submission.case_total * problem.points
                                      if submission.case_total else 0, 1)
            if not problem.partial and submission.points < problem.points:
                submission.points = 0
            submission.save(update_fields=['points'])
            submission.update_contest()
            rescored += 1
            if rescored % 10 == 0:
                p.done = rescored

    with Progress(self, submissions.values('user_id').distinct().count(), stage=_('Recalculating user points')) as p:
        users = 0
        profiles = Profile.objects.filter(id__in=submissions.values_list('user_id', flat=True).distinct())
        for profile in profiles.iterator():
            profile._updating_stats_only = True
            profile.calculate_points()
            cache.delete('user_complete:%d' % profile.id)
            cache.delete('user_attempted:%d' % profile.id)
            users += 1
            if users % 10 == 0:
                p.done = users
    return rescored
