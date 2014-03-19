from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic import TemplateView

from .register import RegistrationView, ActivationView
from .user import *
from .problem import *
from .submission import *


class TemplateView(TemplateView):
    title = None

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs and self.title is not None:
            kwargs['title'] = self.title
        return super(TemplateView, self).get_context_data(**kwargs)


def home(request):
    return render_to_response('index.html', {'title': 'Home'},
                              context_instance=RequestContext(request))


def about(request):
    return render_to_response('about.html', {'title': 'About'},
                              context_instance=RequestContext(request))
