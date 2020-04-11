import logging
import threading
import time
from functools import partial

from django.conf import settings

from judge.bridge.djangohandler import DjangoHandler
from judge.bridge.judgecallback import DjangoJudgeHandler
from judge.bridge.judgelist import JudgeList
from judge.bridge.server import Server
from judge.models import Judge, Submission

logger = logging.getLogger('judge.bridge')


def reset_judges():
    Judge.objects.update(online=False, ping=None, load=None)


def judge_daemon():
    reset_judges()
    Submission.objects.filter(status__in=Submission.IN_PROGRESS_GRADING_STATUS).update(status='IE', result='IE')
    judges = JudgeList()

    judge_server = Server(settings.BRIDGED_JUDGE_ADDRESS, partial(DjangoJudgeHandler, judges=judges))
    django_server = Server(settings.BRIDGED_DJANGO_ADDRESS, partial(DjangoHandler, judges=judges))

    threading.Thread(target=django_server.serve_forever).start()
    threading.Thread(target=judge_server.serve_forever).start()

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        pass
    finally:
        django_server.shutdown()
        judge_server.shutdown()
