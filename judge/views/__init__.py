from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic import TemplateView

from .register import RegistrationView, ActivationView
from .user import users, user, edit_profile
from .problem import problem, problems, problem_submit
from .submission import submission_status, submissions, submission_rank


class TemplateView(TemplateView):
    title = None

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs and self.title is not None:
            kwargs['title'] = self.title
        return super(TemplateView, self).get_context_data(**kwargs)


def home(request):
    return render_to_response('index.html', {'title': 'DMOPC Home'},
                              context_instance=RequestContext(request))
