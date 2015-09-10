from django.core.management.base import BaseCommand

from judge.rabbitmq.handler import AMQPJudgeResponseDaemon


class Command(BaseCommand):
    def handle(self, *args, **options):
        handler = AMQPJudgeResponseDaemon()
        handler.run()
