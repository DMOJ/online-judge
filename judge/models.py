import re
from operator import itemgetter, attrgetter

import pytz
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Max, Sum, Min
from django.utils import timezone
from timedelta.fields import TimedeltaField

from judge.judgeapi import judge_submission, abort_submission
from judge.model_choices import ACE_THEMES
from judge.ordered_model import OrderedModel


def make_timezones():
    data = {}
    for tz in pytz.all_timezones:
        if '/' in tz:
            area, loc = tz.split('/', 1)
        else:
            area, loc = 'Other', tz
        if area in data:
            data[area].append((tz, loc))
        else:
            data[area] = [(tz, loc)]
    data = data.items()
    data.sort(key=itemgetter(0))
    return data


now = timezone.now
TIMEZONE = make_timezones()
del make_timezones


class Language(models.Model):
    key = models.CharField(max_length=6, verbose_name='Short identifier', unique=True)
    name = models.CharField(max_length=20, verbose_name='Long name')
    short_name = models.CharField(max_length=10, verbose_name='Short name', null=True, blank=True)
    common_name = models.CharField(max_length=10, verbose_name='Common name')
    ace = models.CharField(max_length=20, verbose_name='ACE mode name')
    pygments = models.CharField(max_length=20, verbose_name='Pygments Name')
    info = models.CharField(max_length=50, verbose_name='Basic runtime info', blank=True)
    description = models.TextField(verbose_name='Description for model', blank=True)

    @property
    def short_display_name(self):
        return self.short_name or self.key

    def __unicode__(self):
        return self.name

    @property
    def display_name(self):
        if self.info:
            return '%s (%s)' % (self.name, self.info)
        else:
            return self.name

    @classmethod
    def get_python2(cls):
        # We really need a default language, and this app is in Python 2
        return Language.objects.get_or_create(key='PY2', name='Python 2')[0]

    class Meta:
        ordering = ['key']


class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name='User associated')
    name = models.CharField(max_length=50, verbose_name='Display name', null=True, blank=True)
    about = models.TextField(verbose_name='Self-description', null=True, blank=True)
    timezone = models.CharField(max_length=50, verbose_name='Timezone', default='America/Toronto', choices=TIMEZONE)
    language = models.ForeignKey(Language, verbose_name='Default language')
    points = models.FloatField(default=0, db_index=True)
    ace_theme = models.CharField(max_length=30, choices=ACE_THEMES, default='github')
    last_access = models.DateTimeField(verbose_name='Last access time', default=now)
    ip = models.GenericIPAddressField(verbose_name='Last IP', blank=True, null=True)

    def calculate_points(self):
        self.points = sum(map(itemgetter('points'),
                              Submission.objects.filter(user=self, points__isnull=False, problem__is_public=True)
                              .values('problem_id').distinct()
                              .annotate(points=Max('points'))))
        self.save()
        return self.points

    @property
    def display_name(self):
        if self.name:
            return self.name
        return self.user.username

    @property
    def long_display_name(self):
        if self.name:
            return u'%s (%s)' % (self.user.username, self.name)
        return self.user.username

    @property
    def display_rank(self):
        return 'admin' if self.is_admin else ('setter' if self.is_problem_setter else 'user')

    @property
    def is_admin(self):
        return self.user.is_superuser or self.user.groups.filter(name='Admin').exists()

    @property
    def is_problem_setter(self):
        return self.user.is_superuser or self.user.groups.filter(name='ProblemSetter').exists()

    @property
    def problems(self):
        return Submission.objects.filter(user=self, points__gt=0).values('problem').distinct().count()

    @property
    def contest(self):
        cp, created = ContestProfile.objects.get_or_create(user=self)
        if cp.current is not None and cp.current.ended:
            cp.current = None
            cp.save()
        return cp

    def __unicode__(self):
        # return u'Profile of %s in %s speaking %s' % (self.long_display_name(), self.timezone, self.language)
        return self.long_display_name


class ProblemType(models.Model):
    name = models.CharField(max_length=20, verbose_name='Problem category ID', unique=True)
    full_name = models.CharField(max_length=100, verbose_name='Problem category name')

    def __unicode__(self):
        return self.full_name

    class Meta:
        ordering = ['full_name']


class ProblemGroup(models.Model):
    name = models.CharField(max_length=20, verbose_name='Problem group ID', unique=True)
    full_name = models.CharField(max_length=100, verbose_name='Problem group name')

    def __unicode__(self):
        return self.full_name

    class Meta:
        ordering = ['full_name']


class Problem(models.Model):
    code = models.CharField(max_length=20, verbose_name='Problem code', unique=True,
                            validators=[RegexValidator('^[a-z0-9]+$', 'Problem code must be ^[a-z0-9]+$')])
    name = models.CharField(max_length=100, verbose_name='Problem name', db_index=True)
    description = models.TextField(verbose_name='Problem body')
    user = models.ForeignKey(Profile, verbose_name='Creator', null=True, blank=True, default=None)
    types = models.ManyToManyField(ProblemType, verbose_name='Problem types')
    group = models.ForeignKey(ProblemGroup, verbose_name='Problem group')
    time_limit = models.IntegerField(verbose_name='Time limit')
    memory_limit = models.IntegerField(verbose_name='Memory limit')
    short_circuit = models.BooleanField(default=False)
    points = models.FloatField(verbose_name='Points')
    partial = models.BooleanField(verbose_name='Allows partial points')
    allowed_languages = models.ManyToManyField(Language, verbose_name='Allowed languages')
    is_public = models.BooleanField(verbose_name='Publicly visible')

    def types_list(self):
        return map(attrgetter('full_name'), self.types.all())

    def languages_list(self):
        return self.allowed_languages.values_list('common_name', flat=True).distinct().order_by('common_name')

    def number_of_users(self):
        return Submission.objects.filter(problem=self, points__gt=0).values('user').distinct().count()

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('judge.views.problem', args=(self.code,))

    @classmethod
    def unsolved(cls, user, queryset=None):
        if queryset is None:
            queryset = cls.objects
        return queryset.exclude(id__in=Submission.objects.filter(user=user, result='AC')
                                .values_list('problem__id', flat=True))

    class Meta:
        permissions = (
            ('see_private_problem', 'See hidden problems'),
        )


SUBMISSION_RESULT = (
    ('AC', 'Accepted'),
    ('WA', 'Wrong Answer'),
    ('TLE', 'Time Limit Exceeded'),
    ('MLE', 'Memory Limit Exceeded'),
    ('OLE', 'Output Limit Exceeded'),
    ('IR', 'Invalid Return'),
    ('RTE', 'Runtime Error'),
    ('CE', 'Compile Error'),
    ('IE', 'Internal Error'),
    ('AB', 'Aborted'),
)


class Submission(models.Model):
    STATUS = (
        ('QU', 'Queued'),
        ('C', 'Compiled'),
        ('G', 'Grading'),
        ('D', 'Completed'),
        ('IE', 'Internal Error'),
        ('CE', 'Compile Error'),
        ('AB', 'Aborted'),
    )
    RESULT = SUBMISSION_RESULT
    USER_DISPLAY_CODES = {
        'AC': 'Accepted',
        'WA': 'Wrong Answer',
        'SC': "Short Circuited",
        'TLE': 'Time Limit Exceeded',
        'MLE': 'Memory Limit Exceeded',
        'IR': 'Invalid Return',
        'RTE': 'Runtime Error (invalid syscall)',
        'CE': 'Compile Error',
        'IE': 'Internal Error (judging server error)',
        'QU': 'Queued',
        'C': 'Compiled',
        'G': 'Grading',
        'D': 'Completed',
        'AB': 'Aborted',
    }

    user = models.ForeignKey(Profile)
    problem = models.ForeignKey(Problem)
    date = models.DateTimeField(verbose_name='Submission time', auto_now_add=True)
    time = models.FloatField(verbose_name='Execution time', null=True, db_index=True)
    memory = models.FloatField(verbose_name='Memory usage', null=True)
    points = models.FloatField(verbose_name='Points granted', null=True, db_index=True)
    language = models.ForeignKey(Language, verbose_name='Submission language')
    source = models.TextField(verbose_name='Source code')
    status = models.CharField(max_length=2, choices=STATUS, default='QU', db_index=True)
    result = models.CharField(max_length=3, choices=SUBMISSION_RESULT, default=None, null=True,
                              blank=True, db_index=True)
    error = models.TextField(verbose_name='Compile Errors', null=True, blank=True)
    current_testcase = models.IntegerField(default=0)
    batch = models.BooleanField(verbose_name='Batched cases', default=False)
    case_points = models.FloatField(verbose_name='Test case points', default=0)
    case_total = models.FloatField(verbose_name='Test case total points', default=0)

    @property
    def long_status(self):
        return Submission.USER_DISPLAY_CODES.get(self.result if self.result else self.status, '')

    def judge(self):
        return judge_submission(self)

    def abort(self):
        return abort_submission(self)

    def is_graded(self):
        return self.status not in ['QU', 'C', 'G']

    @property
    def contest_key(self):
        if hasattr(self, 'contest'):
            return self.contest.participation.contest.key

    def __unicode__(self):
        return u'Submission %d of %s by %s' % (self.id, self.problem, self.user)

    class Meta:
        permissions = (
            ('rejudge_submission', 'Rejudge the submission'),
            ('rejudge_submission_lot', 'Rejudge a lot of submissions'),
            ('spam_submission', 'Submit without limit')
        )


class SubmissionTestCase(models.Model):
    RESULT = SUBMISSION_RESULT

    submission = models.ForeignKey(Submission, verbose_name='Associated submission', related_name='test_cases')
    case = models.IntegerField(verbose_name='Test case ID')
    status = models.CharField(max_length=3, verbose_name='Status flag', choices=SUBMISSION_RESULT)
    time = models.FloatField(verbose_name='Execution time', null=True)
    memory = models.FloatField(verbose_name='Memory usage', null=True)
    points = models.FloatField(verbose_name='Points granted', null=True)
    total = models.FloatField(verbose_name='Points possible', null=True)
    batch = models.IntegerField(verbose_name='Batch number', null=True)
    feedback = models.CharField(max_length=50, verbose_name='Judging feedback', blank=True)
    output = models.TextField(verbose_name='Program output', blank=True)


class Comment(models.Model):
    author = models.ForeignKey(Profile, verbose_name='Commenter')
    time = models.DateTimeField(verbose_name='Posted time', auto_now_add=True)
    page = models.CharField(max_length=30, verbose_name='Associated Page')
    parent = models.ForeignKey('self', related_name='replies', null=True, blank=True)
    score = models.IntegerField(verbose_name='Votes', default=0)
    title = models.CharField(max_length=200, verbose_name='Title of comment')
    body = models.TextField(verbose_name='Body of comment', blank=True)

    def __unicode__(self):
        return self.title


class CommentVote(models.Model):
    class Meta:
        unique_together = ['voter', 'comment']

    voter = models.ForeignKey(Profile)
    comment = models.ForeignKey(Comment)
    score = models.IntegerField()


class MiscConfig(models.Model):
    key = models.CharField(max_length=30, db_index=True)
    value = models.TextField()


def validate_regex(regex):
    try:
        re.compile(regex, re.VERBOSE)
    except re.error as e:
        raise ValidationError('Invalid regex: %s' % e.message)


class NavigationBar(OrderedModel):
    class Meta:
        ordering = ['order']
        verbose_name = 'navigation item'
        verbose_name_plural = 'navigation bar'

    key = models.CharField(max_length=10, unique=True, verbose_name='Identifier')
    label = models.CharField(max_length=20)
    path = models.CharField(max_length=30, verbose_name='Link path')
    regex = models.TextField(verbose_name='Highlight regex', validators=[validate_regex])

    def __unicode__(self):
        return self.label

    @property
    def pattern(self, cache={}):
        if self.regex in cache:
            return cache[self.regex]
        else:
            pattern = cache[self.regex] = re.compile(self.regex, re.VERBOSE)
            return pattern


class Judge(models.Model):
    name = models.CharField(max_length=50, help_text='Server name, hostname-style', unique=True)
    created = models.DateTimeField(auto_now_add=True)
    auth_key = models.CharField(max_length=100, help_text='A key to authenticated this judge',
                                verbose_name='Authentication key')
    online = models.BooleanField(default=False)
    last_connect = models.DateTimeField(verbose_name='Last connection time', null=True)
    ping = models.FloatField(verbose_name='Response time', null=True)
    load = models.FloatField(verbose_name='System load', null=True,
                             help_text='Load for the last minute, divided by processors to be fair.')
    problems = models.ManyToManyField(Problem)
    runtimes = models.ManyToManyField(Language)

    def __unicode__(self):
        return self.name

    @property
    def uptime(self):
        return timezone.now() - self.last_connect if self.online else 'N/A'

    @property
    def ping_ms(self):
        return self.ping * 1000

    @property
    def runtime_list(self):
        return map(attrgetter('name'), self.runtimes.all())


class Contest(models.Model):
    key = models.CharField(max_length=20, verbose_name='Contest id', unique=True,
                           validators=[RegexValidator('^[a-z0-9]+$', 'Contest id must be ^[a-z0-9]+$')])
    name = models.CharField(max_length=100, verbose_name='Contest name', db_index=True)
    description = models.TextField(blank=True)
    ongoing = models.BooleanField(default=True)
    problems = models.ManyToManyField(Problem, verbose_name='Problems', through='ContestProblem')
    time_limit = TimedeltaField(verbose_name='Time limit')
    is_public = models.BooleanField(verbose_name='Publicly visible', default=False)

    def __unicode__(self):
        return self.name

    class Meta:
        permissions = (
            ('see_private_contest', 'See private contests'),
        )


class ContestParticipation(models.Model):
    contest = models.ForeignKey(Contest, verbose_name='Associated contest', related_name='users')
    profile = models.ForeignKey('ContestProfile', verbose_name='User', related_name='history')
    start = models.DateTimeField(verbose_name='Start time', default=timezone.now)
    score = models.IntegerField(verbose_name='score', default=0, db_index=True)

    def recalculate_score(self):
        self.score = sum(map(itemgetter('points'),
                             self.submissions.values('submission__problem').annotate(points=Max('points'))))
        self.save()
        return self.score

    @property
    def end_time(self):
        return self.start + self.contest.time_limit

    @property
    def ended(self):
        return self.end_time < timezone.now()

    @property
    def time_remaining(self):
        now = timezone.now()
        end = self.end_time
        if end >= now:
            return end - now
        else:
            return None

    def __unicode__(self):
        return '%s in %s' % (self.profile.user.display_name, self.contest.name)


class ContestProfile(models.Model):
    user = models.OneToOneField(Profile, verbose_name='User', related_name='+')
    current = models.OneToOneField(ContestParticipation, verbose_name='Current contest',
                                   null=True, blank=True, related_name='+')

    def __unicode__(self):
        return 'Contest: %s' % self.user.display_name


class ContestProblem(models.Model):
    problem = models.ForeignKey(Problem, related_name='contests')
    contest = models.ForeignKey(Contest, related_name='contest_problems')
    points = models.IntegerField()
    partial = models.BooleanField()

    class Meta:
        unique_together = ('problem', 'contest')


class ContestSubmission(models.Model):
    submission = models.OneToOneField(Submission, related_name='contest')
    problem = models.ForeignKey(ContestProblem, related_name='submissions')
    participation = models.ForeignKey(ContestParticipation, related_name='submissions', related_query_name='submission')
    points = models.FloatField(default=0.0)
