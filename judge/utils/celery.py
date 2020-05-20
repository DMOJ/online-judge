from celery.result import AsyncResult
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import urlencode


class Progress:
    def __init__(self, task, total, stage=None):
        self.task = task
        self._total = total
        self._done = 0
        self._stage = stage

    def _update_state(self):
        self.task.update_state(
            state='PROGRESS',
            meta={
                'done': self._done,
                'total': self._total,
                'stage': self._stage,
            },
        )

    @property
    def done(self):
        return self._done

    @done.setter
    def done(self, value):
        self._done = value
        self._update_state()

    @property
    def total(self):
        return self._total

    @total.setter
    def total(self, value):
        self._total = value
        self._done = min(self._done, value)
        self._update_state()

    def did(self, delta):
        self._done += delta
        self._update_state()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.done = self._total


def task_status_url_by_id(result_id, message=None, redirect=None):
    args = {}
    if message:
        args['message'] = message
    if redirect:
        args['redirect'] = redirect
    url = reverse('task_status', args=[result_id])
    if args:
        url += '?' + urlencode(args)
    return url


def task_status_url(result, message=None, redirect=None):
    return task_status_url_by_id(result.id, message, redirect)


def redirect_to_task_status(result, message=None, redirect=None):
    return HttpResponseRedirect(task_status_url(result, message, redirect))


def task_status_by_id(result_id):
    return AsyncResult(result_id)
