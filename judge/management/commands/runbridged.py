import threading

from django.conf import settings
from django.core.management.base import BaseCommand

from judge.bridge import DjangoHandler, DjangoServer
from judge.bridge import DjangoJudgeHandler, JudgeServer


class Command(BaseCommand):
    def handle(self, *args, **options):
        judge_server = JudgeServer(settings.BRIDGED_JUDGE_HOST, settings.BRIDGED_JUDGE_PORT, DjangoJudgeHandler)
        django_server = DjangoServer(judge_server.judges, settings.BRIDGED_DJANGO_HOST, settings.BRIDGED_DJANGO_PORT,
                                     DjangoHandler)

        # TODO: Merge the two servers
        threading.Thread(target=django_server.serve_forever).start()
        try:
            judge_server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            django_server.stop()