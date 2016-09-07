from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.translation import ugettext as _, ugettext_lazy
from django.views.generic import DetailView, ListView, TemplateView

from judge.models import Language, Judge
from judge.utils.views import generic_message, TitleMixin


class LanguageList(TitleMixin, ListView):
    model = Language
    context_object_name = 'languages'
    template_name = 'language_list.jade'
    title = ugettext_lazy('Runtimes')
