from django.views.generic import TemplateView as OldTemplateView

from .register import RegistrationView, ActivationView
from .contests import *
from .comment import *
from .user import *
from .problem import *
from .submission import *
from .ranked_submission import RankedSubmissions, ContestRankedSubmission
from .status import *
from .widgets import *


class TemplateView(OldTemplateView):
    title = None

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs and self.title is not None:
            kwargs['title'] = self.title
        return super(TemplateView, self).get_context_data(**kwargs)
