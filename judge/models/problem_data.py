import errno
import os
from zipfile import ZipFile

import yaml
from django.db import models
from django.utils.translation import gettext_lazy as _

from judge.utils.problem_data import ProblemDataStorage


__all__ = ['problem_data_storage', 'problem_directory_file', 'ProblemData', 'ProblemTestCase', 'CHECKERS']

problem_data_storage = ProblemDataStorage()


def _problem_directory_file(code, filename):
    return os.path.join(code, os.path.basename(filename))


def problem_directory_file(data, filename):
    return _problem_directory_file(data.problem.code, filename)


CHECKERS = (
    ('standard', _('Standard')),
    ('floats', _('Floats')),
    ('floatsabs', _('Floats (absolute)')),
    ('floatsrel', _('Floats (relative)')),
    ('rstripped', _('Non-trailing spaces')),
    ('sorted', _('Sorted')),
    ('identical', _('Byte identical')),
    ('linecount', _('Line-by-line')),
)


class ProblemData(models.Model):
    problem = models.OneToOneField('Problem', verbose_name=_('problem'), related_name='data_files',
                                   on_delete=models.CASCADE)
    zipfile = models.FileField(verbose_name=_('data zip file'), storage=problem_data_storage, null=True, blank=True,
                               upload_to=problem_directory_file)
    generator = models.FileField(verbose_name=_('generator file'), storage=problem_data_storage, null=True, blank=True,
                                 upload_to=problem_directory_file)
    infer_from_zip = models.BooleanField(verbose_name=_('infer test cases from zip'), null=True, blank=True)
    test_cases_content = models.TextField(verbose_name=_('test cases content'), blank=True)
    output_prefix = models.IntegerField(verbose_name=_('output prefix length'), blank=True, null=True)
    output_limit = models.IntegerField(verbose_name=_('output limit length'), blank=True, null=True)
    feedback = models.TextField(verbose_name=_('init.yml generation feedback'), blank=True)
    checker = models.CharField(max_length=10, verbose_name=_('checker'), choices=CHECKERS, blank=True)
    unicode = models.BooleanField(verbose_name=_('enable unicode'), null=True, blank=True)
    nobigmath = models.BooleanField(verbose_name=_('disable bigInteger / bigDecimal'), null=True, blank=True)
    checker_args = models.TextField(verbose_name=_('checker arguments'), blank=True,
                                    help_text=_('Checker arguments as a JSON object.'))

    __original_zipfile = None

    def __init__(self, *args, **kwargs):
        super(ProblemData, self).__init__(*args, **kwargs)
        self.__original_zipfile = self.zipfile

        if not self.zipfile:
            # Test cases not loaded through the site, but some data has been found within the problem folder
            if self.has_yml():
                self.feedback = 'Warning: problem data found within the file system, but none has been setup '\
                                'using this site. No actions are needed if the problem is working as intended; '\
                                "otherwise, you can <a id='perform_infer_test_cases' href='javascript:void(0);'>"\
                                'infer the testcases using the existing zip file (one entry per file within the '\
                                "zip)</a> or <a id='perform_rebuild_test_cases' href='javascript:void(0);'>"\
                                'rebuild the test cases using the existing yml file as a template (only works'\
                                'with simple problems)</a>.'

    def save(self, *args, **kwargs):
        zipfile = self.zipfile
        if self.zipfile != self.__original_zipfile:
            self.__original_zipfile.delete(save=False)  # This clears both zip fields (original and current)
            self.zipfile = zipfile  # Needed to restore the newly uploaded zip file when replacing an old one
        return super(ProblemData, self).save(*args, **kwargs)

    def has_yml(self):
        return problem_data_storage.exists('%s/init.yml' % self.problem.code)

    def _update_code(self, original, new):
        try:
            problem_data_storage.rename(original, new)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        if self.zipfile:
            self.zipfile.name = _problem_directory_file(new, self.zipfile.name)
        if self.generator:
            self.generator.name = _problem_directory_file(new, self.generator.name)
        self.save()
    _update_code.alters_data = True

    def setup_test_cases_content(self):
        self.test_cases_content = ''

        if self.zipfile:
            zip = ZipFile(self.zipfile)

            last = 0
            content = []
            test_cases = ProblemTestCase.objects.filter(dataset_id=self.problem.pk)

            for i, tc in enumerate([x for x in test_cases if x.is_pretest]):
                self.append_tescase_to_statement(zip, content, tc, i)
                last = i

            if last > 0:
                last += 1

            for i, tc in enumerate([x for x in test_cases if not x.is_pretest]):
                self.append_tescase_to_statement(zip, content, tc, i + last)

            self.test_cases_content = '\n'.join(content)

    def append_tescase_to_statement(self, zip, content, tc, i):
        content.append(f'## Sample Input {i+1}')
        content.append('')

        if tc.is_private:
            content.append('*Hidden: this is a private test case!*  ')

        else:
            content.append('```')
            content.append(zip.read(tc.input_file).decode('utf-8'))
            content.append('```')

        content.append('')
        content.append(f'## Sample Output {i+1}')
        content.append('')

        if tc.is_private:
            content.append('*Hidden: this is a private test case!*  ')

        else:
            content.append('```')
            content.append(zip.read(tc.output_file).decode('utf-8'))
            content.append('```')

        content.append('')

    def infer_test_cases_from_zip(self):
        # Just infers the zip data into ProblemTestCase objects, without changes in the database.
        # It will try to mantain existing test cases data if the input and output entries are the same.
        if not self.zipfile:
            # The zip file will be loaded from the file system if not provided
            files = problem_data_storage.listdir(self.problem.code)[1]
            zipfiles = [x for x in files if '.zip' in x]

            if len(zipfiles) > 0:
                self.zipfile = _problem_directory_file(self.problem.code, zipfiles[0])
            else:
                raise FileNotFoundError

        files = sorted(ZipFile(self.zipfile).namelist())
        input = [x for x in files if '.in' in x or ('input' in x and '.' in x)]
        output = [x for x in files if '.out' in x or ('output' in x and '.' in x)]

        cases = []
        for i in range(len(input)):
            list = ProblemTestCase.objects.filter(dataset_id=self.problem.pk, input_file=input[i],
                                                  output_file=output[i])
            if len(list) >= 1:
                # Multiple test-cases for the same data is allowed, but strange. Using object.get() produces an
                # exception.
                ptc = list[0]
            else:
                ptc = ProblemTestCase()
                ptc.dataset = self.problem
                ptc.is_pretest = False
                ptc.is_private = False
                ptc.order = i
                ptc.input_file = input[i]
                ptc.output_file = output[i]
                ptc.points = 0

            cases.append(ptc)

        return cases

    def reload_test_cases_from_yml(self):
        cases = []
        if self.has_yml():
            yml = problem_data_storage.open('%s/init.yml' % self.problem.code)
            doc = yaml.safe_load(yml)

            # Load same YML data as in site/judge/utils/problem_data.py -> ProblemDataCompiler()
            if doc.get('archive'):
                self.zipfile = _problem_directory_file(self.problem.code, doc['archive'])

            if doc.get('generator'):
                self.generator = _problem_directory_file(self.problem.code, doc['generator'])

            if doc.get('pretest_test_cases'):
                self.pretest_test_cases = doc['pretest_test_cases']

            if doc.get('output_limit_length'):
                self.output_limit = doc['output_limit_length']

            if doc.get('output_prefix_length'):
                self.output_prefix = doc['output_prefix_length']

            if doc.get('unicode'):
                self.unicode = doc['unicode']

            if doc.get('nobigmath'):
                self.nobigmath = doc['nobigmath']

            if doc.get('checker'):
                self.checker = doc['checker']

            if doc.get('hints'):
                for h in doc['hints']:
                    if h == 'unicode':
                        self.unicode = True
                    if h == 'nobigmath':
                        self.nobigmath = True

            if doc.get('pretest_test_cases'):
                cases += self._load_test_case_from_doc(doc, 'pretest_test_cases', True)

            if doc.get('test_cases'):
                cases += self._load_test_case_from_doc(doc, 'test_cases', False)

        return cases

    def _load_test_case_from_doc(self, doc, field, is_pretest):
        cases = []
        for i, test in enumerate(doc[field]):
            ptc = ProblemTestCase()
            ptc.dataset = self.problem
            ptc.is_pretest = is_pretest
            ptc.order = i

            if test.get('type'):
                ptc.type = test['type']

            if test.get('in'):
                ptc.input_file = test['in']

            if test.get('out'):
                ptc.output_file = test['out']

            if test.get('points'):
                ptc.points = test['points']
            else:
                ptc.points = 0

            if test.get('is_private'):
                ptc.is_private = test['is_private']

            if test.get('generator_args'):
                args = []
                for arg in test['generator_args']:
                    args.append(arg)

                ptc.generator_args = '\n'.join(args)

            if test.get('output_prefix_length'):
                ptc.output_prefix = doc['output_prefix_length']

            if test.get('output_limit_length'):
                ptc.output_limit = doc['output_limit_length']

            if test.get('checker'):
                chk = test['checker']
                if isinstance(chk, str):
                    ptc.checker = chk
                else:
                    ptc.checker = chk['name']
                    ptc.checker_args = chk['args']

            cases.append(ptc)

        return cases


class ProblemTestCase(models.Model):
    dataset = models.ForeignKey('Problem', verbose_name=_('problem data set'), related_name='cases',
                                on_delete=models.CASCADE)
    order = models.IntegerField(verbose_name=_('case position'))
    type = models.CharField(max_length=1, verbose_name=_('case type'),
                            choices=(('C', _('Normal case')),
                                     ('S', _('Batch start')),
                                     ('E', _('Batch end'))),
                            default='C')
    input_file = models.CharField(max_length=100, verbose_name=_('input file name'), blank=True)
    output_file = models.CharField(max_length=100, verbose_name=_('output file name'), blank=True)
    generator_args = models.TextField(verbose_name=_('generator arguments'), blank=True)
    points = models.IntegerField(verbose_name=_('point value'), blank=True, null=True)
    is_pretest = models.BooleanField(verbose_name=_('case is pretest?'), default=False)
    is_private = models.BooleanField(verbose_name=_('case is private?'), default=False)
    output_prefix = models.IntegerField(verbose_name=_('output prefix length'), blank=True, null=True)
    output_limit = models.IntegerField(verbose_name=_('output limit length'), blank=True, null=True)
    checker = models.CharField(max_length=10, verbose_name=_('checker'), choices=CHECKERS, blank=True)
    checker_args = models.TextField(verbose_name=_('checker arguments'), blank=True,
                                    help_text=_('checker arguments as a JSON object'))
    batch_dependencies = models.TextField(verbose_name=_('batch dependencies'), blank=True,
                                          help_text=_('batch dependencies as a comma-separated list of integers'))
