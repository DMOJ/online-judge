from django.shortcuts import render_to_response
from django.template import RequestContext

__author__ = 'Quantum'


def generic_message(request, title, message):
    return render_to_response('generic_message.jade', {
        'message': message,
        'title': title
    }, context_instance=RequestContext(request))