from django.http import Http404
from django.shortcuts import render
from django.views.generic import DetailView

from judge.utils.views import TitleMixin, generic_message
from judge.models import Judge


__all__ = ['status_all', 'status_table']


def status_all(request):
    return render(request, 'judge_status.jade', {
        'judges': Judge.objects.all(),
        'title': 'Status',
    })


def status_table(request):
    return render(request, 'judge_status_table.jade', {
        'judges': Judge.objects.all(),
    })


class JudgeDetail(TitleMixin, DetailView):
    model = Judge
    context_object_name = 'judge'
    slug_field = 'name'
    slug_url_kwarg = 'name'
    template_name = 'judge.jade'

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(JudgeDetail, self).dispatch(request, *args, **kwargs)
        except Http404:
            key = kwargs.get(self.slug_url_kwarg, None)
            return generic_message(request, 'No such judge',
                                   'Could not find a judge with the name "%s".' % key)

    def get_title(self):
        return 'Judge %s' % self.object.name

    def get_context_data(self, **kwargs):
        context = super(JudgeDetail, self).get_context_data(**kwargs)
        context['judges'] = Judge.objects.all()
        return context
