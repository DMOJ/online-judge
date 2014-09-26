from django.shortcuts import render_to_response
from django.template import RequestContext

from judge.models import Judge

__all__ = ['status']


def status(request):
    return render_to_response('status.jade', {
        'judges': Judge.objects.all(),
        'title': 'Status',
    }, context_instance=RequestContext(request))