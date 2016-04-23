from django.apps import AppConfig
from django.utils.translation import ugettext_lazy


class JudgeAppConfig(AppConfig):
    name = 'judge'
    verbose_name = ugettext_lazy('Online Judge')

    def ready(self):
        # WARNING: AS THIS IS NOT A FUNCTIONAL PROGRAMMING LANGUAGE,
        #          OPERATIONS MAY HAVE SIDE EFFECTS.
        #          DO NOT REMOVE THINKING THE IMPORT IS UNUSED.
        from . import signals

        from django.contrib.flatpages.models import FlatPage
        from reversion.helpers import patch_admin
        patch_admin(FlatPage)