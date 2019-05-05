from celery import shared_task

from judge.models import Submission
from judge.utils.celery import Progress

__all__ = ('rejudge_problem_all', 'rejudge_problem_by_id')


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
