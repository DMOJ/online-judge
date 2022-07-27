import logging
import socket

from celery import Celery
from celery.signals import task_failure

app = Celery('dmoj')

from django.conf import settings  # noqa: E402, I202, django must be imported here
app.config_from_object(settings, namespace='CELERY')

if hasattr(settings, 'CELERY_BROKER_URL_SECRET'):
    app.conf.broker_url = settings.CELERY_BROKER_URL_SECRET
if hasattr(settings, 'CELERY_RESULT_BACKEND_SECRET'):
    app.conf.result_backend = settings.CELERY_RESULT_BACKEND_SECRET

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Logger to enable reporting of errors.
logger = logging.getLogger('judge.celery')


@task_failure.connect()
def celery_failure_log(sender, task_id, exception, traceback, *args, **kwargs):
    logger.error('Celery Task %s: %s on %s', sender.name, task_id, socket.gethostname(),  # noqa: G201
                 exc_info=(type(exception), exception, traceback))
