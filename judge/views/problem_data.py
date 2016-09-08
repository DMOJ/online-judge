import mimetypes
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.forms import ModelForm
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import DetailView

from judge.models import ProblemData, Problem
from judge.utils.views import TitleMixin
from judge.views.problem import ProblemMixin

mimetypes.init()


class ProblemDataForm(ModelForm):
    class Meta:
        model = ProblemData
        fields = ['zipfile', 'generator', 'output_limit', 'output_prefix']


class ProblemDataView(LoginRequiredMixin, TitleMixin, ProblemMixin, DetailView):
    template_name = 'problem/data.jade'

    def get_title(self):
        return _('Editing data for %s') % self.object.name

    def get_object(self, queryset=None):
        problem = super(ProblemDataView, self).get_object(queryset)
        if self.request.user.is_superuser or problem.authors.filter(id=self.request.user.profile.id).exists():
            return problem
        raise Http404()

    def get_data_form(self, post=False):
        return ProblemDataForm(data=self.request.POST if post else None, prefix='problem-data',
                               files=self.request.FILES if post else None,
                               instance=ProblemData.objects.get_or_create(problem=self.object)[0])

    def get_context_data(self, **kwargs):
        context = super(ProblemDataView, self).get_context_data(**kwargs)
        if 'data_form' not in context:
            context['data_form'] = self.get_data_form()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        data_form = self.get_data_form(post=True)
        if data_form.is_valid():
            data_form.save()
            return HttpResponseRedirect(request.get_full_path())
        return self.render_to_response(self.get_context_data(data_form=data_form))

    put = post


@login_required
def problem_data_file(request, problem, path):
    object = get_object_or_404(Problem, code=problem)
    if not request.user.is_superuser and not object.authors.filter(id=request.user.profile.id).exists():
        raise Http404()

    response = HttpResponse()
    if hasattr(settings, 'PROBLEM_DATA_INTERNAL') and request.META.get('SERVER_SOFTWARE', '').startswith('nginx/'):
        response['X-Accel-Redirect'] = '%s/%s/%s' % (settings.PROBLEM_DATA_INTERNAL, problem, path)
    elif hasattr(settings, 'PROBLEM_DATA_ROOT'):
        with open(os.path.join(settings.PROBLEM_DATA_ROOT, problem, path), 'rb') as f:
            response.content = f.read()
    else:
        return HttpResponseRedirect(default_storage.url('%s/%s' % (problem, path)))

    response['Content-Type'] = mimetypes.guess_type(path)
    return response
