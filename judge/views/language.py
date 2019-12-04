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
        queryset = super().get_queryset().prefetch_related('runtimeversion_set')
        if not self.request.user.is_superuser and not self.request.user.is_staff:
            queryset = queryset.filter(judges__online=True).distinct()
        return queryset
