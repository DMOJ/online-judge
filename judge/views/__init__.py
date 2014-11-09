from django.contrib.flatpages.models import FlatPage
from django.contrib.flatpages.views import flatpage
from django.views.generic import TemplateView

from .register import RegistrationView, ActivationView
from .contests import *
from .comment import *
from .user import *
from .problem import *
from .submission import *
from .ranked_submission import RankedSubmissions
from .status import *
from .widgets import *


class TemplateView(TemplateView):
    title = None

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs and self.title is not None:
            kwargs['title'] = self.title
        return super(TemplateView, self).get_context_data(**kwargs)


def home(request):
    if FlatPage.objects.filter(url='/').exists():
        return flatpage(request, '/')
    return render_to_response('base.jade', {'title': 'Home'},
                              context_instance=RequestContext(request))
