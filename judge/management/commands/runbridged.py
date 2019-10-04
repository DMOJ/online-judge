import threading

from django.conf import settings
from django.core.management.base import BaseCommand

from judge.bridge import DjangoHandler, DjangoServer
from judge.bridge import DjangoJudgeHandler, JudgeServer


class Command(BaseCommand):
    def handle(self, *args, **options):
        judge_handler = DjangoJudgeHandler

        try:
            import netaddr  # noqa: F401, imported to see if it exists
        except ImportError:
            pass
        else:
            proxies = settings.BRIDGED_JUDGE_PROXIES
            if proxies:
                judge_handler = judge_handler.with_proxy_set(proxies)

        judge_server = JudgeServer(settings.BRIDGED_JUDGE_ADDRESS, judge_handler)
        django_server = DjangoServer(judge_server.judges, settings.BRIDGED_DJANGO_ADDRESS, DjangoHandler)

        # TODO: Merge the two servers
        threading.Thread(target=django_server.serve_forever).start()
        try:
            judge_server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            django_server.stop()
