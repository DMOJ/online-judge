from celery import shared_task

__all__ = ('success', 'failure')


@shared_task
def success():
    pass


@shared_task
def failure():
    raise RuntimeError('This task always fails.')
