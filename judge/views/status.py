from itertools import chain

from django.http import Http404
from django.shortcuts import render
from django.utils.translation import ugettext as _
from django.views.generic import DetailView

from judge.models import Judge
from judge.utils.views import TitleMixin, generic_message


__all__ = ['status_all', 'status_table']


def get_judges(request):
    last_online_time = Judge.last_online_time()
    if request.user.is_superuser or request.user.is_staff:
        return True, list(chain(Judge.objects.filter(last_ping__gte=last_online_time),
                                Judge.objects.exclude(last_ping__gte=last_online_time)))
    else:
        return False, Judge.objects.filter(last_ping__gte=last_online_time)


def status_all(request):
    see_all, judges = get_judges(request)
    return render(request, 'judge_status.jade', {
        'title': _('Status'),
        'judges': judges,
        'see_all_judges': see_all,
    })


def status_table(request):
    see_all, judges = get_judges(request)
    return render(request, 'judge_status_table.jade', {
        'judges': judges,
        'see_all_judges': see_all,
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
            return generic_message(request, _('No such judge'),
                                   _('Could not find a judge with the name "%s".') % key)

    def get_title(self):
        return 'Judge %s' % self.object.name

    def get_context_data(self, **kwargs):
        context = super(JudgeDetail, self).get_context_data(**kwargs)
        context['see_all_judges'], context['judges'] = get_judges(self.request)
        return context
