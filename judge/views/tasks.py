from functools import partial

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from judge.tasks import success, failure


def demo_task(request, task):
    if not request.user.is_superuser:
        raise PermissionDenied()
    result = task.delay()
    return HttpResponse('Task %s scheduled.' % (result.id,))


demo_success = partial(demo_task, task=success)
demo_failure = partial(demo_task, task=failure)
