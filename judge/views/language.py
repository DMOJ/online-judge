from django.utils.translation import gettext_lazy
from django.views.generic import ListView

from judge.models import Language
from judge.utils.views import TitleMixin


class LanguageList(TitleMixin, ListView):
    model = Language
    context_object_name = 'languages'
    template_name = 'status/language-list.html'
    title = gettext_lazy('Runtimes')

    def get_queryset(self):
        return super(LanguageList, self).get_queryset().prefetch_related('runtimeversion_set')
