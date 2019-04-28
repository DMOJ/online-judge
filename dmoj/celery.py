import logging
import os
import socket

from celery import Celery
from celery.signals import task_failure

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmoj.settings')

app = Celery('dmoj')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Logger to enable errors be reported.
logger = logging.getLogger('judge.celery')


@task_failure.connect()
def celery_failure_log(sender, task_id, exception, traceback, *args, **kwargs):
    logger.exception('Celery Task {task_name}: {task_id} on {hostname}'.format(
        task_name=sender.name, task_id=task_id, hostname=socket.gethostname()
    ), exc_info=(type(exception), exception, traceback))
