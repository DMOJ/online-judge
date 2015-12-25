from django.apps import AppConfig
from django.utils.translation import ugettext_lazy


class JudgeAppConfig(AppConfig):
    name = 'judge'
    verbose_name = ugettext_lazy('Online Judge')

    def ready(self):
        from . import signals

        from django.contrib.flatpages.models import FlatPage
        from reversion.helpers import patch_admin
        patch_admin(FlatPage)