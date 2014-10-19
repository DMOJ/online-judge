from django.shortcuts import render_to_response
from django.template import RequestContext

from judge.models import Judge

__all__ = ['status', 'status_table']


def status(request):
    return render_to_response('judge_status.jade', {
        'judges': Judge.objects.all(),
        'title': 'Status',
    }, context_instance=RequestContext(request))


def status_table(request):
    return render_to_response('judge_status_table.jade', {
        'judges': Judge.objects.all().order_by('load'),
    }, context_instance=RequestContext(request))
