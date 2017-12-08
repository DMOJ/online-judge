import json
import mimetypes
import os
from itertools import chain
from zipfile import ZipFile, BadZipfile

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.forms import ModelForm, formset_factory, HiddenInput, NumberInput, Select, BaseModelFormSet
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.generic import DetailView

from judge.highlight_code import highlight_code
from judge.models import ProblemData, Problem, ProblemTestCase, problem_data_storage
from judge.utils.problem_data import ProblemDataCompiler
from judge.utils.views import TitleMixin
from judge.views.problem import ProblemMixin

mimetypes.init()
mimetypes.add_type('application/x-yaml', '.yml')


def checker_args_cleaner(self):
    data = self.cleaned_data['checker_args']
    if not data or data.isspace():
        return ''
    try:
        if not isinstance(json.loads(data), dict):
            raise ValidationError(_('Checker arguments must be a JSON object'))
    except ValueError:
        raise ValidationError(_('Checker arguments is invalid JSON'))
    return data


class ProblemDataForm(ModelForm):
    def clean_zipfile(self):
        if hasattr(self, 'zip_valid') and not self.zip_valid:
            raise ValidationError(_('Your zip file is invalid!'))
        return self.cleaned_data['zipfile']

    clean_checker_args = checker_args_cleaner

    class Meta:
        model = ProblemData
        fields = ['zipfile', 'generator', 'output_limit', 'output_prefix', 'checker', 'checker_args']
        widgets = {
            'checker_args': HiddenInput,
        }


class ProblemCaseForm(ModelForm):
    clean_checker_args = checker_args_cleaner

    class Meta:
        model = ProblemTestCase
        fields = ('order', 'type', 'input_file', 'output_file', 'points',
                  'is_pretest', 'output_limit', 'output_prefix', 'checker', 'checker_args', 'generator_args')
        widgets = {
            'generator_args': HiddenInput,
            'type': Select(attrs={'style': 'width: 100%'}),
            'points': NumberInput(attrs={'style': 'width: 4em'}),
            'output_prefix': NumberInput(attrs={'style': 'width: 4.5em'}),
            'output_limit': NumberInput(attrs={'style': 'width: 6em'}),
            'checker_args': HiddenInput,
        }


class ProblemCaseFormSet(formset_factory(ProblemCaseForm, formset=BaseModelFormSet, extra=1, max_num=1, can_delete=True)):
    model = ProblemTestCase

    def __init__(self, *args, **kwargs):
        self.valid_files = kwargs.pop('valid_files', None)
        super(ProblemCaseFormSet, self).__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        form = super(ProblemCaseFormSet, self)._construct_form(i, **kwargs)
        form.valid_files = self.valid_files
        return form


class ProblemDataView(LoginRequiredMixin, TitleMixin, ProblemMixin, DetailView):
    template_name = 'problem/data.html'

    def get_title(self):
        return _('Editing data for %s') % self.object.name

    def get_content_title(self):
        return mark_safe(escape(_('Editing data for %s')) % (
            format_html(u'<a href="{1}">{0}</a>', self.object.name,
                        reverse('problem_detail', args=[self.object.code]))))

    def get_object(self, queryset=None):
        problem = super(ProblemDataView, self).get_object(queryset)
        if problem.is_manually_managed:
            raise Http404()
        if self.request.user.is_superuser or problem.is_editable_by(self.request.user):
            return problem
        raise Http404()

    def get_data_form(self, post=False):
        return ProblemDataForm(data=self.request.POST if post else None, prefix='problem-data',
                               files=self.request.FILES if post else None,
                               instance=ProblemData.objects.get_or_create(problem=self.object)[0])

    def get_case_formset(self, files, post=False):
        return ProblemCaseFormSet(data=self.request.POST if post else None, prefix='cases', valid_files=files,
                                  queryset=ProblemTestCase.objects.filter(dataset_id=self.object.pk).order_by('order'))

    def get_valid_files(self, data, post=False):
        try:
            if post and 'problem-data-zipfile-clear' in self.request.POST:
                return []
            elif post and 'problem-data-zipfile' in self.request.FILES:
                return ZipFile(self.request.FILES['problem-data-zipfile']).namelist()
            elif data.zipfile:
                return ZipFile(data.zipfile.path).namelist()
        except BadZipfile:
            return []
        return []

    def get_context_data(self, **kwargs):
        context = super(ProblemDataView, self).get_context_data(**kwargs)
        if 'data_form' not in context:
            context['data_form'] = self.get_data_form()
            valid_files = context['valid_files'] = self.get_valid_files(context['data_form'].instance)
            context['data_form'].zip_valid = valid_files is not False
            context['cases_formset'] = self.get_case_formset(valid_files)
        context['valid_files_json'] = mark_safe(json.dumps(context['valid_files']))
        context['valid_files'] = set(context['valid_files'])
        context['all_case_forms'] = chain(context['cases_formset'], [context['cases_formset'].empty_form])
        return context

    def post(self, request, *args, **kwargs):
        self.object = problem = self.get_object()
        data_form = self.get_data_form(post=True)
        valid_files = self.get_valid_files(data_form.instance, post=True)
        data_form.zip_valid = valid_files is not False
        cases_formset = self.get_case_formset(valid_files, post=True)
        if data_form.is_valid() and cases_formset.is_valid():
            data = data_form.save()
            for case in cases_formset.save(commit=False):
                case.dataset_id = problem.id
                case.save()
            for case in cases_formset.deleted_objects:
                case.delete()
            ProblemDataCompiler.generate(problem, data, problem.cases.order_by('order'), valid_files)
            return HttpResponseRedirect(request.get_full_path())
        return self.render_to_response(self.get_context_data(data_form=data_form, cases_formset=cases_formset,
                                                             valid_files=valid_files))

    put = post


@login_required
def problem_data_file(request, problem, path):
    object = get_object_or_404(Problem, code=problem)
    if not object.is_editable_by(request.user):
        raise Http404()

    response = HttpResponse()
    if hasattr(settings, 'PROBLEM_DATA_INTERNAL') and request.META.get('SERVER_SOFTWARE', '').startswith('nginx/'):
        response['X-Accel-Redirect'] = '%s/%s/%s' % (settings.PROBLEM_DATA_INTERNAL, problem, path)
    else:
        try:
            with problem_data_storage.open(os.path.join(problem, path), 'rb') as f:
                response.content = f.read()
        except IOError:
            raise Http404()

    type, encoding = mimetypes.guess_type(path)
    response['Content-Type'] = type or 'application/octet-stream'
    if encoding is not None:
        response['Content-Encoding'] = encoding
    return response


@login_required
def problem_init_view(request, problem):
    problem = get_object_or_404(Problem, code=problem)
    if not request.user.is_superuser and not problem.is_editable_by(request.user):
        raise Http404()

    try:
        with problem_data_storage.open(os.path.join(problem.code, 'init.yml')) as f:
            data = f.read().rstrip('\n')
    except IOError:
        raise Http404()

    return render(request, 'problem/yaml.html', {
        'raw_source': data, 'highlighted_source': highlight_code(data, 'yaml'),
        'title': _('Generated init.yml for %s') % problem.name,
        'content_title': mark_safe(escape(_('Generated init.yml for %s')) % (
            format_html(u'<a href="{1}">{0}</a>', problem.name,
                        reverse('problem_detail', args=[problem.code]))))
    })
