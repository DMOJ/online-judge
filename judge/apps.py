from django.apps import AppConfig


class JudgeAppConfig(AppConfig):
    name = 'judge'

    def ready(self):
        from . import signals

        from django.contrib.flatpages.models import FlatPage
        from reversion.helpers import patch_admin
        patch_admin(FlatPage)