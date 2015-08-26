from django.apps import AppConfig


class JudgeAppConfig(AppConfig):
    name = 'judge'

    def ready(self):
        from . import signals