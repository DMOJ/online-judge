from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.forms import ModelForm
from django.http import HttpResponseRedirect
from django.views.generic import DetailView

from judge.models import ProblemData
from judge.views.problem import ProblemMixin


class ProblemDataForm(ModelForm):
    class Meta:
        model = ProblemData
        fields = ['zipfile', 'generator', 'output_limit', 'output_prefix']


class ProblemDataView(LoginRequiredMixin, ProblemMixin, DetailView):
    template_name = 'problem/data.jade'

    def get_object(self, queryset=None):
        problem = super(ProblemDataView, self).get_object(queryset)
        if self.request.user.is_superuser or problem.authors.filter(id=self.request.user.profile).exists():
            return problem
        raise PermissionDenied()

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
