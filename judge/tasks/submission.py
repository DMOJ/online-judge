from celery import shared_task
from django.core.cache import cache
from django.utils.translation import gettext as _

from judge.models import Submission, Profile, Problem
from judge.utils.celery import Progress

__all__ = ('rejudge_problem_all', 'rejudge_problem_by_id', 'rescore_problem')


def rejudge_queryset(task, queryset):
    rejudged = 0
    with Progress(task, queryset.count()) as p:
        for submission in queryset.iterator():
            submission.judge(rejudge=True)
            rejudged += 1
            if rejudged % 10 == 0:
                p.done = rejudged
    return rejudged


@shared_task(bind=True)
def rejudge_problem_all(self, problem_id):
    queryset = Submission.objects.filter(problem_id=problem_id)
    return rejudge_queryset(self, queryset)


@shared_task(bind=True)
def rejudge_problem_by_id(self, problem_id, start, end):
    queryset = Submission.objects.filter(problem_id=problem_id, id__gte=start, id__lte=end)
    return rejudge_queryset(self, queryset)


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
