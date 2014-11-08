from django.shortcuts import render_to_response
from django.template import RequestContext

__author__ = 'Quantum'


def generic_message(request, title, message):
    return render_to_response('generic_message.jade', {
        'message': message,
        'title': title
    }, context_instance=RequestContext(request))


class TitleMixin(object):
    def get_context_data(self, **kwargs):
        context = super(TitleMixin, self).get_context_data(**kwargs)
        context['title'] = self.get_title()
        return context

    def get_title(self):
        return self.title
