from django.http import Http404
from django.views.generic import DetailView, ListView
from judge.models import Language
from judge.utils.views import generic_message, TitleMixin


class LanguageDetail(TitleMixin, DetailView):
    model = Language
    context_object_name = 'language'
    slug_field = 'key'
    slug_url_kwarg = 'key'
    template_name = 'language.jade'

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(LanguageDetail, self).dispatch(request, *args, **kwargs)
        except Http404:
            key = kwargs.get(self.slug_url_kwarg, None)
            return generic_message(request, 'No such language',
                                   'Could not find a language with the key "%s".' % key)

    def get_title(self):
        return self.object.name


class LanguageList(TitleMixin, ListView):
    model = Language
    context_object_name = 'languages'
    template_name = 'language_list.jade'
    title = 'Runtimes'
