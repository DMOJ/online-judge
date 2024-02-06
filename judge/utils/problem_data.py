import json
import os
import re

import yaml
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.utils.translation import gettext as _

if os.altsep:
    def split_path_first(path, repath=re.compile('[%s]' % re.escape(os.sep + os.altsep))):
        return repath.split(path, 1)
else:
    def split_path_first(path):
        return path.split(os.sep, 1)


class ProblemDataStorage(FileSystemStorage):
    def __init__(self):
        super(ProblemDataStorage, self).__init__(settings.DMOJ_PROBLEM_DATA_ROOT)

    def url(self, name):
        path = split_path_first(name)
        if len(path) != 2:
            raise ValueError('This file is not accessible via a URL.')
        return reverse('problem_data_file', args=path)

    def _save(self, name, content):
        if self.exists(name):
            self.delete(name)
        return super(ProblemDataStorage, self)._save(name, content)

    def get_available_name(self, name, max_length=None):
        return name

    def rename(self, old, new):
        return os.rename(self.path(old), self.path(new))


class ProblemDataError(Exception):
    def __init__(self, message):
        super(ProblemDataError, self).__init__(message)
        self.message = message


class ProblemDataCompiler(object):
    def __init__(self, problem, data, cases, files):
        self.problem = problem
        self.data = data
        self.cases = cases
        self.files = files

        self.generator = data.generator

    def make_init(self):
        cases = []
        batch = None
        batch_count = 0

        def end_batch():
            if not batch['batched']:
                raise ProblemDataError(_('Empty batches not allowed.'))
            cases.append(batch)

        def make_checker(case):
            if case.checker_args:
                return {
                    'name': case.checker,
                    'args': json.loads(case.checker_args),
                }
            return case.checker

        for i, case in enumerate(self.cases, 1):
            if case.type == 'C':
                data = {}
                if batch:
                    case.points = None
                    case.is_pretest = batch['is_pretest']
                else:
                    if case.points is None:
                        raise ProblemDataError(_('Points must be defined for non-batch case #%d.') % i)
                    data['is_pretest'] = case.is_pretest

                if not self.generator:
                    if case.input_file not in self.files:
                        raise ProblemDataError(_('Input file for case %d does not exist: %s') %
                                               (i, case.input_file))
                    if case.output_file not in self.files:
                        raise ProblemDataError(_('Output file for case %d does not exist: %s') %
                                               (i, case.output_file))

                if case.input_file:
                    data['in'] = case.input_file
                if case.output_file:
                    data['out'] = case.output_file
                if case.points is not None:
                    data['points'] = case.points
                if case.generator_args:
                    data['generator_args'] = case.generator_args.splitlines()
                if case.output_limit is not None:
                    data['output_limit_length'] = case.output_limit
                if case.output_prefix is not None:
                    data['output_prefix_length'] = case.output_prefix
                if case.checker:
                    data['checker'] = make_checker(case)
                else:
                    case.checker_args = ''
                case.save(update_fields=('checker_args', 'is_pretest'))
                (batch['batched'] if batch else cases).append(data)
            elif case.type == 'S':
                batch_count += 1
                if batch:
                    end_batch()
                if case.points is None:
                    raise ProblemDataError(_('Batch start case #%d requires points.') % i)
                dependencies = []
                if case.batch_dependencies.strip():
                    try:
                        dependencies = list(map(int, case.batch_dependencies.split(',')))
                    except ValueError:
                        raise ProblemDataError(
                            _('Dependencies must be a comma-separated list of integers for batch start case #%d.') % i,
                        )
                    for batch_number in dependencies:
                        if batch_number >= batch_count:
                            raise ProblemDataError(
                                _('Dependencies must depend on previous batches for batch start case #%d.') % i,
                            )
                        elif batch_number < 1:
                            raise ProblemDataError(_('Dependencies must be positive for batch start case #%d.') % i)
                batch = {
                    'points': case.points,
                    'batched': [],
                    'is_pretest': case.is_pretest,
                    'dependencies': dependencies,
                }
                if case.generator_args:
                    batch['generator_args'] = case.generator_args.splitlines()
                if case.output_limit is not None:
                    batch['output_limit_length'] = case.output_limit
                if case.output_prefix is not None:
                    batch['output_prefix_length'] = case.output_prefix
                if case.checker:
                    batch['checker'] = make_checker(case)
                else:
                    case.checker_args = ''
                case.input_file = ''
                case.output_file = ''
                case.save(update_fields=('checker_args', 'input_file', 'output_file'))
            elif case.type == 'E':
                if not batch:
                    raise ProblemDataError(_('Attempt to end batch outside of one in case #%d.') % i)
                case.is_pretest = batch['is_pretest']
                case.input_file = ''
                case.output_file = ''
                case.generator_args = ''
                case.checker = ''
                case.checker_args = ''
                case.save()
                end_batch()
                batch = None
        if batch:
            end_batch()

        init = {}

        if self.data.zipfile:
            zippath = split_path_first(self.data.zipfile.name)
            if len(zippath) != 2:
                raise ProblemDataError(_('How did you corrupt the zip path?'))
            init['archive'] = zippath[1]

        if self.generator:
            generator_path = split_path_first(self.generator.name)
            if len(generator_path) != 2:
                raise ProblemDataError(_('How did you corrupt the generator path?'))
            init['generator'] = generator_path[1]

        pretest_test_cases = []
        test_cases = []
        hints = []

        for case in cases:
            if case['is_pretest']:
                pretest_test_cases.append(case)
            else:
                test_cases.append(case)

            del case['is_pretest']

        if pretest_test_cases:
            init['pretest_test_cases'] = pretest_test_cases
        if test_cases:
            init['test_cases'] = test_cases
        if self.data.output_limit is not None:
            init['output_limit_length'] = self.data.output_limit
        if self.data.output_prefix is not None:
            init['output_prefix_length'] = self.data.output_prefix
        if self.data.unicode:
            hints.append('unicode')
        if self.data.nobigmath:
            hints.append('nobigmath')
        if self.data.checker:
            init['checker'] = make_checker(self.data)
        else:
            self.data.checker_args = ''

        if hints:
            init['hints'] = hints

        return init

    def compile(self):
        from judge.models import problem_data_storage

        yml_file = '%s/init.yml' % self.problem.code
        try:
            init = self.make_init()
            if init:
                init = yaml.safe_dump(init)
        except ProblemDataError as e:
            self.data.feedback = e.message
            self.data.save()
            problem_data_storage.delete(yml_file)
        else:
            self.data.feedback = ''
            self.data.save()
            if init:
                problem_data_storage.save(yml_file, ContentFile(init))
            else:
                # Don't write empty init.yml since we should be looking in manually managed
                # judge-server#670 will not update cache on empty init.yml,
                # but will do so if there is no init.yml, so we delete the init.yml
                problem_data_storage.delete(yml_file)

    @classmethod
    def generate(cls, *args, **kwargs):
        self = cls(*args, **kwargs)
        self.compile()
