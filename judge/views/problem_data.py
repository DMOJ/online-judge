import mimetypes
import os
from zipfile import ZipFile, BadZipfile

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.forms import ModelForm, formset_factory, HiddenInput, NumberInput, BaseModelFormSet
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import DetailView

from judge.models import ProblemData, Problem, ProblemTestCase
from judge.utils.views import TitleMixin
from judge.views.problem import ProblemMixin

mimetypes.init()


class ProblemDataForm(ModelForm):
    def clean_zipfile(self):
        if hasattr(self, 'zip_valid') and not self.zip_valid:
            raise ValidationError(_('Your zip file is invalid!'))
        return self.cleaned_data['zipfile']

    class Meta:
        model = ProblemData
        fields = ['zipfile', 'generator', 'output_limit', 'output_prefix']


class ProblemCaseForm(ModelForm):
    def clean_input_file(self):
        if not self.valid_files or self.cleaned_data['input_file'] not in self.valid_files:
            raise ValidationError(_('Input file is not a valid problem data file.'))
        return self.cleaned_data['input_file']

    def clean_output_file(self):
        if not self.valid_files or self.cleaned_data['output_file'] not in self.valid_files:
            raise ValidationError(_('Output file is not a valid problem data file.'))
        return self.cleaned_data['output_file']

    class Meta:
        model = ProblemTestCase
        fields = ('order', 'type', 'input_file', 'output_file', 'points',
                  'is_pretest', 'output_limit', 'output_prefix', 'generator_args')
        widgets = {
            'generator_args': HiddenInput,
            'points': NumberInput(attrs={'style': 'width: 4em'}),
            'output_prefix': NumberInput(attrs={'style': 'width: 4.5em'}),
            'output_limit': NumberInput(attrs={'style': 'width: 6em'}),
        }


class ProblemCaseFormSet(formset_factory(ProblemCaseForm, formset=BaseModelFormSet, extra=10, can_delete=True)):
    model = ProblemTestCase

    def __init__(self, *args, **kwargs):
        self.valid_files = kwargs.pop('valid_files', None)
        super(ProblemCaseFormSet, self).__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        form = super(ProblemCaseFormSet, self)._construct_form(i, **kwargs)
        form.valid_files = self.valid_files
        return form


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

    def get_case_formset(self, files, post=False):
        return ProblemCaseFormSet(data=self.request.POST if post else None, prefix='cases', valid_files=files,
                                  queryset=ProblemTestCase.objects.filter(dataset_id=self.object.pk))

    def get_valid_files(self, data, post=False):
        try:
            if post and 'problem-data-zipfile-clear' in self.request.POST:
                return set()
            elif post and 'problem-data-zipfile' in self.request.FILES:
                return ZipFile(self.request.FILES['problem-data-zipfile']).namelist()
            elif data.zipfile is not None:
                return ZipFile(data.zipfile.path).namelist()
        except BadZipfile:
            return False
        return set()

    def get_context_data(self, **kwargs):
        context = super(ProblemDataView, self).get_context_data(**kwargs)
        if 'data_form' not in context:
            context['data_form'] = self.get_data_form()
            valid_files = self.get_valid_files(context['data_form'].instance)
            context['data_form'].zip_valid = valid_files is not False
            context['cases_formset'] = self.get_case_formset(valid_files)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        data_form = self.get_data_form(post=True)
        valid_files = self.get_valid_files(data_form.instance, post=True)
        data_form.zip_valid = valid_files is not False
        cases_formset = self.get_case_formset(valid_files, post=True)
        if data_form.is_valid() and cases_formset.is_valid():
            data = data_form.save()
            for case in cases_formset.save(commit=False):
                case.dataset = data
                case.save()
            return HttpResponseRedirect(request.get_full_path())
        return self.render_to_response(self.get_context_data(data_form=data_form, cases_formset=cases_formset))

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

    response['Content-Type'] = mimetypes.guess_type(path)[0]
    return response
