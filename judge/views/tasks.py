import json
from functools import partial
from uuid import UUID

from celery.result import AsyncResult
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import is_safe_url

from judge.tasks import failure, progress, success
from judge.utils.celery import redirect_to_task_status
from judge.utils.views import short_circuit_middleware


def get_task_status(task_id):
    result = AsyncResult(task_id)
    info = result.result
    if result.state == 'PROGRESS':
        return {'code': 'PROGRESS', 'done': info['done'], 'total': info['total'], 'stage': info['stage']}
    elif result.state == 'SUCCESS':
        return {'code': 'SUCCESS'}
    elif result.state == 'FAILURE':
        return {'code': 'FAILURE', 'error': str(info)}
    else:
        return {'code': 'WORKING'}


def task_status(request, task_id):
    try:
        UUID(task_id)
    except ValueError:
        raise Http404()

    redirect = request.GET.get('redirect')
    if not is_safe_url(redirect, allowed_hosts={request.get_host()}):
        redirect = None

    status = get_task_status(task_id)
    if status['code'] == 'SUCCESS' and redirect:
        return HttpResponseRedirect(redirect)

    return render(request, 'task_status.html', {
        'task_id': task_id, 'task_status': json.dumps(status),
        'message': request.GET.get('message', ''), 'redirect': redirect or '',
    })


@short_circuit_middleware
def task_status_ajax(request):
    if 'id' not in request.GET:
        return HttpResponseBadRequest('Need to pass GET parameter "id"', content_type='text/plain')
    return JsonResponse(get_task_status(request.GET['id']))


def demo_task(request, task, message):
    if not request.user.is_superuser:
        raise PermissionDenied()
    result = task.delay()
    return redirect_to_task_status(result, message=message, redirect=reverse('home'))


demo_success = partial(demo_task, task=success, message='Running example task that succeeds...')
demo_failure = partial(demo_task, task=failure, message='Running example task that fails...')
demo_progress = partial(demo_task, task=progress, message='Running example task that waits 10 seconds...')
