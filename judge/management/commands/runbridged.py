import threading
import time

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from judge.bridge import DjangoJudgeHandler, JudgeServer
from judge.bridge import DjangoHandler, DjangoServer


class Command(BaseCommand):
    def handle(self, *args, **options):
        judge_server = JudgeServer((settings.BRIDGED_JUDGE_HOST, settings.BRIDGED_JUDGE_PORT), DjangoJudgeHandler)
        django_server = DjangoServer(judge_server.judges, (settings.BRIDGED_DJANGO_HOST, settings.BRIDGED_DJANGO_PORT),
                                     DjangoHandler)

        judge_server.daemon_threads = True
        django_server.daemon_threads = True

        # TODO: This is so ugly. Would be so much prettier to have select() on both of them.
        threading.Thread(target=judge_server.serve_forever).start()
        threading.Thread(target=django_server.serve_forever).start()
        try:
            while True:
                time.sleep(86400)
        except KeyboardInterrupt:
            django_server.shutdown()
            judge_server.shutdown()