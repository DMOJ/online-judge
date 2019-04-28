import time

from celery import shared_task

from judge.utils.celery import Progress

__all__ = ('success', 'failure', 'progress')


@shared_task
def success():
    pass


@shared_task
def failure():
    raise RuntimeError('This task always fails.')


@shared_task(bind=True)
def progress(self, seconds=10):
    with Progress(self, seconds) as p:
        for i in range(seconds):
            time.sleep(1)
            p.did(1)
