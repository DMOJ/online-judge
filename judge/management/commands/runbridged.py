import logging
import threading
import time
from functools import partial

from django.conf import settings
from django.core.management.base import BaseCommand

from judge.bridge import DjangoHandler, JudgeList
from judge.bridge import DjangoJudgeHandler
from judge.bridge.server import Server
from judge.models import Judge, Submission

logger = logging.getLogger('judge.bridge')


def reset_judges():
    Judge.objects.update(online=False, ping=None, load=None)


def ping_judges(judges):
    try:
        while True:
            for judge in judges:
                judge.ping()
            time.sleep(10)
    except Exception:
        logger.exception('Ping error')
        raise


class Command(BaseCommand):
    def handle(self, *args, **options):
        reset_judges()
        Submission.objects.filter(status__in=Submission.IN_PROGRESS_GRADING_STATUS).update(status='IE', result='IE')
        judges = JudgeList()

        judge_server = Server(settings.BRIDGED_JUDGE_ADDRESS, partial(DjangoJudgeHandler, judges=judges))
        django_server = Server(settings.BRIDGED_DJANGO_ADDRESS, partial(DjangoHandler, judges=judges))

        ping_thread = threading.Thread(target=ping_judges, kwargs={'judges': judges})
        ping_thread.daemon = True
        ping_thread.start()

        threading.Thread(target=django_server.serve_forever).start()
        try:
            judge_server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            django_server.shutdown()
