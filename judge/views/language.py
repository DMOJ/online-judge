from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.views.generic import DetailView, ListView, TemplateView
from judge.models import Language, Judge
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

    def get_context_data(self, **kwargs):
        context = super(LanguageDetail, self).get_context_data(**kwargs)
        context['judges'] = self.object.judges.order_by('load')
        return context


class LanguageList(TitleMixin, ListView):
    model = Language
    context_object_name = 'languages'
    template_name = 'language_list.jade'
    title = 'Runtimes'


class LanguageJudgesAjaxList(TemplateView):
    template_name = 'judge_status_table.jade'

    def get(self, request, *args, **kwargs):
        self.lang = kwargs.pop('key', None)
        if self.lang is None:
            raise ImproperlyConfigured('Need lang')
        return super(LanguageJudgesAjaxList, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(LanguageJudgesAjaxList, self).get_context_data(**kwargs)
        context['judges'] = Judge.objects.filter(runtimes__key=self.lang).order_by('load')
        return context
