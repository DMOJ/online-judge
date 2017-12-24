from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from judge.judgeapi import judge_submission, abort_submission
from judge.models.problem import Problem, TranslatedProblemForeignKeyQuerySet
from judge.models.profile import Profile
from judge.models.runtime import Language

__all__ = ['SUBMISSION_RESULT', 'Submission', 'SubmissionTestCase']

SUBMISSION_RESULT = (
    ('AC', _('Accepted')),
    ('WA', _('Wrong Answer')),
    ('TLE', _('Time Limit Exceeded')),
    ('MLE', _('Memory Limit Exceeded')),
    ('OLE', _('Output Limit Exceeded')),
    ('IR', _('Invalid Return')),
    ('RTE', _('Runtime Error')),
    ('CE', _('Compile Error')),
    ('IE', _('Internal Error')),
    ('SC', _('Short circuit')),
    ('AB', _('Aborted')),
)


class Submission(models.Model):
    STATUS = (
        ('QU', _('Queued')),
        ('P', _('Processing')),
        ('G', _('Grading')),
        ('D', _('Completed')),
        ('IE', _('Internal Error')),
        ('CE', _('Compile Error')),
        ('AB', _('Aborted')),
    )
    RESULT = SUBMISSION_RESULT
    USER_DISPLAY_CODES = {
        'AC': _('Accepted'),
        'WA': _('Wrong Answer'),
        'SC': "Short Circuited",
        'TLE': _('Time Limit Exceeded'),
        'MLE': _('Memory Limit Exceeded'),
        'OLE': _('Output Limit Exceeded'),
        'IR': _('Invalid Return'),
        'RTE': _('Runtime Error'),
        'CE': _('Compile Error'),
        'IE': _('Internal Error (judging server error)'),
        'QU': _('Queued'),
        'P': _('Processing'),
        'G': _('Grading'),
        'D': _('Completed'),
        'AB': _('Aborted'),
    }

    user = models.ForeignKey(Profile)
    problem = models.ForeignKey(Problem)
    date = models.DateTimeField(verbose_name=_('submission time'), auto_now_add=True, db_index=True)
    time = models.FloatField(verbose_name=_('execution time'), null=True, db_index=True)
    memory = models.FloatField(verbose_name=_('memory usage'), null=True)
    points = models.FloatField(verbose_name=_('points granted'), null=True, db_index=True)
    language = models.ForeignKey(Language, verbose_name=_('submission language'))
    source = models.TextField(verbose_name=_('source code'), max_length=65536)
    status = models.CharField(verbose_name=_('status'), max_length=2, choices=STATUS, default='QU', db_index=True)
    result = models.CharField(verbose_name=_('result'), max_length=3, choices=SUBMISSION_RESULT,
                              default=None, null=True, blank=True, db_index=True)
    error = models.TextField(verbose_name=_('compile errors'), null=True, blank=True)
    current_testcase = models.IntegerField(default=0)
    batch = models.BooleanField(verbose_name=_('batched cases'), default=False)
    case_points = models.FloatField(verbose_name=_('test case points'), default=0)
    case_total = models.FloatField(verbose_name=_('test case total points'), default=0)
    judged_on = models.ForeignKey('Judge', verbose_name=_('judged on'), null=True, blank=True,
                                  on_delete=models.SET_NULL)
    was_rejudged = models.BooleanField(verbose_name=_('was rejudged by admin'), default=False)
    is_pretested = models.BooleanField(verbose_name=_('was ran on pretests only'), default=False)

    objects = TranslatedProblemForeignKeyQuerySet.as_manager()

    @classmethod
    def result_class_from_code(cls, result, case_points, case_total):
        if result == 'AC':
            if case_points == case_total:
                return 'AC'
            return '_AC'
        return result

    @property
    def result_class(self):
        # This exists to save all these conditionals from being executed (slowly) in each row.jade template
        if self.status in ('IE', 'CE'):
            return self.status
        return Submission.result_class_from_code(self.result, self.case_points, self.case_total)

    @property
    def memory_bytes(self):
        return self.memory * 1024 if self.memory is not None else 0

    @property
    def short_status(self):
        return self.result or self.status

    @property
    def long_status(self):
        return Submission.USER_DISPLAY_CODES.get(self.short_status, '')

    def judge(self, rejudge):
        judge_submission(self, rejudge)

    judge.alters_data = True

    def abort(self):
        abort_submission(self)

    abort.alters_data = True

    @property
    def is_graded(self):
        return self.status not in ('QU', 'P', 'G')

    @property
    def contest_key(self):
        if hasattr(self, 'contest'):
            return self.contest.participation.contest.key

    def __unicode__(self):
        return u'Submission %d of %s by %s' % (self.id, self.problem, self.user.user.username)

    def get_absolute_url(self):
        return reverse('submission_status', args=(self.id,))

    @cached_property
    def contest_or_none(self):
        try:
            return self.contest
        except ObjectDoesNotExist:
            return None

    class Meta:
        permissions = (
            ('abort_any_submission', 'Abort any submission'),
            ('rejudge_submission', 'Rejudge the submission'),
            ('rejudge_submission_lot', 'Rejudge a lot of submissions'),
            ('spam_submission', 'Submit without limit'),
            ('view_all_submission', 'View all submission'),
            ('resubmit_other', "Resubmit others' submission"),
        )
        verbose_name = _('submission')
        verbose_name_plural = _('submissions')


class SubmissionTestCase(models.Model):
    RESULT = SUBMISSION_RESULT

    submission = models.ForeignKey(Submission, verbose_name=_('associated submission'), related_name='test_cases')
    case = models.IntegerField(verbose_name=_('test case ID'))
    status = models.CharField(max_length=3, verbose_name=_('status flag'), choices=SUBMISSION_RESULT)
    time = models.FloatField(verbose_name=_('execution time'), null=True)
    memory = models.FloatField(verbose_name=_('memory usage'), null=True)
    points = models.FloatField(verbose_name=_('points granted'), null=True)
    total = models.FloatField(verbose_name=_('points possible'), null=True)
    batch = models.IntegerField(verbose_name=_('batch number'), null=True)
    feedback = models.CharField(max_length=50, verbose_name=_('judging feedback'), blank=True)
    output = models.TextField(verbose_name=_('program output'), blank=True)

    @property
    def long_status(self):
        return Submission.USER_DISPLAY_CODES.get(self.status, '')

    class Meta:
        verbose_name = _('submission test case')
        verbose_name_plural = _('submission test cases')
