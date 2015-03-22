import re
from collections import defaultdict
from operator import itemgetter, attrgetter
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.core.cache import cache
from django.db import transaction
from mptt.fields import TreeForeignKey
from mptt.managers import TreeManager
from mptt.models import MPTTModel

import pytz
import reversion
from django.utils.functional import cached_property
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Max
from django.utils import timezone
from timedelta.fields import TimedeltaField

from judge.fulltext import SearchManager
from judge.judgeapi import judge_submission, abort_submission
from judge.model_choices import ACE_THEMES


def make_timezones():
    data = defaultdict(list)
    for tz in pytz.all_timezones:
        if '/' in tz:
            area, loc = tz.split('/', 1)
        else:
            area, loc = 'Other', tz
        if not loc.startswith('GMT'):
            data[area].append((tz, loc))
    data = data.items()
    data.sort(key=itemgetter(0))
    return data


now = timezone.now
TIMEZONE = make_timezones()
del make_timezones


def fix_unicode(string, unsafe=tuple(u'\u202a\u202b\u202d\u202e')):
    return string + (sum(k in unsafe for k in string) - string.count(u'\u202c')) * u'\u202c'


class Language(models.Model):
    key = models.CharField(max_length=6, verbose_name='Short identifier', unique=True)
    name = models.CharField(max_length=20, verbose_name='Long name')
    short_name = models.CharField(max_length=10, verbose_name='Short name', null=True, blank=True)
    common_name = models.CharField(max_length=10, verbose_name='Common name')
    ace = models.CharField(max_length=20, verbose_name='ACE mode name')
    pygments = models.CharField(max_length=20, verbose_name='Pygments Name')
    info = models.CharField(max_length=50, verbose_name='Basic runtime info', blank=True)
    description = models.TextField(verbose_name='Description for model', blank=True)

    @cached_property
    def short_display_name(self):
        return self.short_name or self.key

    def __unicode__(self):
        return self.name

    @cached_property
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


class Organization(models.Model):
    name = models.CharField(max_length=50, verbose_name='Organization title')
    key = models.CharField(max_length=6, verbose_name='Identifier', unique=True,
                           help_text='Organization name shows in URL',
                           validators=[RegexValidator('^[A-Za-z0-9]+$',
                                                      'Identifier must contain letters and numbers only')])
    short_name = models.CharField(max_length=20, verbose_name='Short name',
                                  help_text='Displayed beside user name during contests')
    about = models.TextField(verbose_name='Organization description')
    registrant = models.ForeignKey('Profile', verbose_name='Registrant',
                                   related_name='registrant+',
                                   help_text='User who registered this organization')
    admins = models.ManyToManyField('Profile', verbose_name='Administrators', related_name='+',
                                    help_text='Those who can edit this organization')
    creation_date = models.DateTimeField(verbose_name='Creation date', auto_now_add=True)

    def __unicode__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()

    def get_absolute_url(self):
        return reverse('organization_home', args=(self.key,))

    class Meta:
        ordering = ['key']


class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name='User associated')
    name = models.CharField(max_length=50, verbose_name='Display name', null=True, blank=True)
    about = models.TextField(verbose_name='Self-description', null=True, blank=True)
    timezone = models.CharField(max_length=50, verbose_name='Location', choices=TIMEZONE,
                                default=getattr(settings, 'DEFAULT_USER_TIME_ZONE', 'America/Toronto'))
    language = models.ForeignKey(Language, verbose_name='Preferred language')
    points = models.FloatField(default=0, db_index=True)
    ace_theme = models.CharField(max_length=30, choices=ACE_THEMES, default='github')
    last_access = models.DateTimeField(verbose_name='Last access time', default=now)
    ip = models.GenericIPAddressField(verbose_name='Last IP', blank=True, null=True)
    organization = models.ForeignKey(Organization, verbose_name='Organization', null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='members', related_query_name='member')
    organization_join_time = models.DateTimeField(verbose_name='Organization joining date', null=True, blank=True)
    display_rank = models.CharField(max_length=10, default='user',
                                    choices=(('user', 'Normal User'), ('setter', 'Problem Setter'), ('admin', 'Admin')))
    mute = models.BooleanField(verbose_name='Comment mute', help_text='Some users are at their best when silent.',
                               default=False)
    rating = models.IntegerField(null=True, default=None)

    def calculate_points(self):
        points = sum(map(itemgetter('points'),
                         Submission.objects.filter(user=self, points__isnull=False, problem__is_public=True)
                         .values('problem_id').distinct()
                         .annotate(points=Max('points'))))
        if self.points != points:
            self.points = points
            self.save()
        return points

    @cached_property
    def display_name(self):
        if self.name:
            return self.name
        return self.user.username

    @cached_property
    def long_display_name(self):
        if self.name:
            return u'%s (%s)' % (self.user.username, self.name)
        return self.user.username

    @cached_property
    def contest(self):
        cp, created = ContestProfile.objects.get_or_create(user=self)
        if cp.current is not None and cp.current.ended:
            cp.current = None
            cp.save()
        return cp

    @cached_property
    def solved_problems(self):
        return Submission.objects.filter(user_id=self.id, points__gt=0).values('problem').distinct().count()

    def get_absolute_url(self):
        return reverse('user_page', args=(self.user.username,))

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
    authors = models.ManyToManyField(Profile, verbose_name='Creators', blank=True, related_name='authored_problems')
    types = models.ManyToManyField(ProblemType, verbose_name='Problem types')
    group = models.ForeignKey(ProblemGroup, verbose_name='Problem group')
    time_limit = models.FloatField(verbose_name='Time limit')
    memory_limit = models.IntegerField(verbose_name='Memory limit')
    short_circuit = models.BooleanField(default=False)
    points = models.FloatField(verbose_name='Points')
    partial = models.BooleanField(verbose_name='Allows partial points')
    allowed_languages = models.ManyToManyField(Language, verbose_name='Allowed languages')
    is_public = models.BooleanField(verbose_name='Publicly visible', db_index=True)
    date = models.DateTimeField(verbose_name='Date of publishing', null=True, blank=True, db_index=True,
                                help_text="Doesn't have magic ability to auto-publish due to backward compatibility")
    banned_users = models.ManyToManyField(Profile, verbose_name='Personae non gratae', blank=True,
                                          help_text='Bans the selected users from submitting to this problem')

    objects = SearchManager(('code', 'name', 'description'))

    def types_list(self):
        return map(attrgetter('full_name'), self.types.all())

    def languages_list(self):
        return self.allowed_languages.values_list('common_name', flat=True).distinct().order_by('common_name')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('problem_detail', args=(self.code,))

    @cached_property
    def author_ids(self):
        return self.authors.values_list('id', flat=True)

    @cached_property
    def usable_languages(self):
        return self.allowed_languages.filter(judges__in=self.judges.filter(online=True)).distinct()

    class Meta:
        permissions = (
            ('see_private_problem', 'See hidden problems'),
            ('edit_own_problem', 'Edit own problems'),
            ('edit_all_problem', 'Edit all problems'),
            ('clone_problem', 'Clone problem'),
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
        ('P', 'Processing'),
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
        'OLE': 'Output Limit Exceeded',
        'IR': 'Invalid Return',
        'RTE': 'Runtime Error',
        'CE': 'Compile Error',
        'IE': 'Internal Error (judging server error)',
        'QU': 'Queued',
        'P': 'Processing',
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
    source = models.TextField(verbose_name='Source code', max_length=65536)
    status = models.CharField(max_length=2, choices=STATUS, default='QU', db_index=True)
    result = models.CharField(max_length=3, choices=SUBMISSION_RESULT, default=None, null=True,
                              blank=True, db_index=True)
    error = models.TextField(verbose_name='Compile Errors', null=True, blank=True)
    current_testcase = models.IntegerField(default=0)
    batch = models.BooleanField(verbose_name='Batched cases', default=False)
    case_points = models.FloatField(verbose_name='Test case points', default=0)
    case_total = models.FloatField(verbose_name='Test case total points', default=0)

    @property
    def memory_bytes(self):
        return self.memory * 1024 if self.memory is not None else 0

    @property
    def short_status(self):
        return self.result or self.status

    @property
    def long_status(self):
        return Submission.USER_DISPLAY_CODES.get(self.short_status, '')

    def judge(self):
        return judge_submission(self)

    def abort(self):
        return abort_submission(self)

    def is_graded(self):
        return self.status not in ('QU', 'P', 'G')

    @property
    def contest_key(self):
        if hasattr(self, 'contest'):
            return self.contest.participation.contest.key

    def __unicode__(self):
        return u'Submission %d of %s by %s' % (self.id, self.problem, self.user)

    def get_absolute_url(self):
        return reverse('submission_status', args=(self.id,))

    class Meta:
        permissions = (
            ('abort_any_submission', 'Abort any submission'),
            ('rejudge_submission', 'Rejudge the submission'),
            ('rejudge_submission_lot', 'Rejudge a lot of submissions'),
            ('spam_submission', 'Submit without limit'),
            ('view_all_submission', 'View all submission'),
            ('resubmit_other', "Resubmit others' submission"),
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

    @property
    def long_status(self):
        return Submission.USER_DISPLAY_CODES.get(self.status, '')


class Comment(MPTTModel):
    author = models.ForeignKey(Profile, verbose_name='Commenter')
    time = models.DateTimeField(verbose_name='Posted time', auto_now_add=True)
    page = models.CharField(max_length=30, verbose_name='Associated Page',
                            validators=[RegexValidator('^[pc]:[a-z0-9]+$|^b:\d+$|^s:',
                                                       'Page code must be ^[pc]:[a-z0-9]+$|^b:\d+$')])
    score = models.IntegerField(verbose_name='Votes', default=0)
    title = models.CharField(max_length=200, verbose_name='Title of comment')
    body = models.TextField(verbose_name='Body of comment', blank=True)
    hidden = models.BooleanField(verbose_name='Hide the comment', default=0)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='replies')

    class MPTTMeta:
        order_insertion_by = ['-time']

    @cached_property
    def link(self):
        link = None
        if self.page.startswith('p:'):
            link = reverse('problem_detail', args=(self.page[2:],))
        elif self.page.startswith('c:'):
            link = reverse('contest_view', args=(self.page[2:],))
        elif self.page.startswith('b:'):
            key = 'blog_slug:%s' % self.page[2:]
            slug = cache.get(key)
            if slug is None:
                try:
                    slug = BlogPost.objects.get(id=self.page[2:]).slug
                except ObjectDoesNotExist:
                    slug = ''
                cache.set(key, slug, 3600)
            link = reverse('blog_post', args=(self.page[2:], slug))
        elif self.page.startswith('s:'):
            link = reverse('solution', args=(self.page[2:],))
        return link

    @cached_property
    def page_title(self):
        try:
            if self.page.startswith('p:'):
                return Problem.objects.get(code=self.page[2:]).name
            elif self.page.startswith('c:'):
                return Contest.objects.get(key=self.page[2:]).name
            elif self.page.startswith('b:'):
                return BlogPost.objects.get(id=self.page[2:]).title
            elif self.page.startswith('s:'):
                return Solution.objects.get(url=self.page[2:]).title
            return '<unknown>'
        except ObjectDoesNotExist:
            return '<deleted>'

    def get_absolute_url(self):
        return '%s#comment-%d-link' % (self.link, self.id)

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
    value = models.TextField(blank=True)

    def __unicode__(self):
        return self.key


def validate_regex(regex):
    try:
        re.compile(regex, re.VERBOSE)
    except re.error as e:
        raise ValidationError('Invalid regex: %s' % e.message)


class NavigationBar(MPTTModel):
    class Meta:
        verbose_name = 'navigation item'
        verbose_name_plural = 'navigation bar'

    class MPTTMeta:
        order_insertion_by = ['order']

    order = models.PositiveIntegerField(db_index=True)
    key = models.CharField(max_length=10, unique=True, verbose_name='Identifier')
    label = models.CharField(max_length=20)
    path = models.CharField(max_length=30, verbose_name='Link path')
    regex = models.TextField(verbose_name='Highlight regex', validators=[validate_regex])
    parent = TreeForeignKey('self', verbose_name='Parent item', null=True, blank=True, related_name='children')

    def __unicode__(self):
        return self.label

    @property
    def pattern(self, cache={}):
        # A cache with a bad policy is an alias for memory leak
        # Thankfully, there will never be too many regexes to cache.
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
    description = models.TextField(blank=True)
    problems = models.ManyToManyField(Problem, related_name='judges')
    runtimes = models.ManyToManyField(Language, related_name='judges')

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

    class Meta:
        ordering = ['-online', 'load']


class Contest(models.Model):
    key = models.CharField(max_length=20, verbose_name='Contest id', unique=True,
                           validators=[RegexValidator('^[a-z0-9]+$', 'Contest id must be ^[a-z0-9]+$')])
    name = models.CharField(max_length=100, verbose_name='Contest name', db_index=True)
    organizers = models.ManyToManyField(Profile, help_text='These people will be able to edit the contest.',
                                        related_name='organizers+')
    description = models.TextField(blank=True)
    problems = models.ManyToManyField(Problem, verbose_name='Problems', through='ContestProblem')
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    time_limit = TimedeltaField(verbose_name='Time limit', blank=True, null=True)
    is_public = models.BooleanField(verbose_name='Publicly visible', default=False)
    is_external = models.BooleanField(verbose_name='External contest', default=False)
    is_rated = models.BooleanField(help_text='Whether this contest can be rated.', default=False)
    rate_all = models.BooleanField(help_text='Rate all users who joined.', default=False)
    rate_exclude = models.ManyToManyField(Profile, verbose_name='exclude from ratings', blank=True,
                                          related_name='rate_exclude+')

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError('What is this? A contest that ended before it starts?')

    @cached_property
    def can_join(self):
        return self.start_time <= timezone.now() < self.end_time

    @property
    def time_before_start(self):
        now = timezone.now()
        if self.start_time >= now:
            return self.start_time - now
        else:
            return None

    @property
    def time_before_end(self):
        now = timezone.now()
        if self.end_time >= now:
            return self.end_time - now
        else:
            return None

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('contest_view', args=(self.key,))

    class Meta:
        permissions = (
            ('see_private_contest', 'See private contests'),
            ('edit_own_contest', 'Edit own contests'),
            ('edit_all_contest', 'Edit all contests'),
            ('contest_rating', 'Rate contests'),
        )


class ContestParticipation(models.Model):
    contest = models.ForeignKey(Contest, verbose_name='Associated contest', related_name='users')
    profile = models.ForeignKey('ContestProfile', verbose_name='User', related_name='history')
    real_start = models.DateTimeField(verbose_name='Start time', default=timezone.now, db_column='start')
    score = models.IntegerField(verbose_name='score', default=0, db_index=True)
    cumtime = models.PositiveIntegerField(verbose_name='Cumulative time', default=0)

    def recalculate_score(self):
        self.score = sum(map(itemgetter('points'),
                             self.submissions.values('submission__problem').annotate(points=Max('points'))))
        self.save()
        return self.score

    @cached_property
    def start(self):
        contest = self.contest
        return contest.start_time if contest.time_limit is None else self.real_start

    @cached_property
    def end_time(self):
        contest = self.contest
        return contest.end_time if contest.time_limit is None else self.real_start + contest.time_limit

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

    def update_cumtime(self):
        cumtime = 0
        profile_id = self.profile.user_id
        for problem in self.contest.contest_problems.all():
            solution = problem.submissions.filter(submission__user_id=profile_id, points__gt=0) \
                .values('submission__user_id').annotate(time=Max('submission__date'))
            if not solution:
                continue
            dt = solution[0]['time'] - self.start
            cumtime += dt.days * 86400 + dt.seconds
        self.cumtime = cumtime
        self.save()

    def __unicode__(self):
        return '%s in %s' % (self.profile.user.long_display_name, self.contest.name)


class ContestProfile(models.Model):
    user = models.OneToOneField(Profile, verbose_name='User', related_name='contest_profile',
                                related_query_name='contest')
    current = models.OneToOneField(ContestParticipation, verbose_name='Current contest',
                                   null=True, blank=True, related_name='+', on_delete=models.SET_NULL)

    def __unicode__(self):
        return 'Contest: %s' % self.user.long_display_name


class ContestProblem(models.Model):
    problem = models.ForeignKey(Problem, related_name='contests')
    contest = models.ForeignKey(Contest, related_name='contest_problems')
    points = models.IntegerField()
    partial = models.BooleanField()

    class Meta:
        unique_together = ('problem', 'contest')


class ContestSubmission(models.Model):
    submission = models.OneToOneField(Submission, related_name='contest')
    problem = models.ForeignKey(ContestProblem, related_name='submissions', related_query_name='submission')
    participation = models.ForeignKey(ContestParticipation, related_name='submissions', related_query_name='submission')
    points = models.FloatField(default=0.0)


class Rating(models.Model):
    user = models.ForeignKey(Profile, related_name='ratings')
    contest = models.ForeignKey(Contest, related_name='ratings')
    participation = models.OneToOneField(ContestParticipation, related_name='rating')
    rank = models.IntegerField()
    rating = models.IntegerField()
    volatility = models.IntegerField()
    last_rated = models.DateTimeField(db_index=True)

    class Meta:
        unique_together = ('user', 'contest')


class BlogPost(models.Model):
    title = models.CharField(verbose_name='Post title', max_length=100)
    slug = models.SlugField(verbose_name='Slug')
    visible = models.BooleanField(verbose_name='Public visibility')
    sticky = models.BooleanField(verbose_name='Sticky')
    publish_on = models.DateTimeField(verbose_name='Publish after')
    content = models.TextField(verbose_name='Post content')
    summary = models.TextField(verbose_name='Post summary', blank=True)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog_post', args=(self.id, self.slug))

    class Meta:
        permissions = (
            ('see_hidden_post', 'See hidden posts'),
        )


class PrivateMessage(models.Model):
    title = models.CharField(verbose_name='Message title', max_length=50)
    content = models.TextField(verbose_name='Message body')
    sender = models.ForeignKey(Profile, verbose_name='Sender', related_name='sent_messages')
    target = models.ForeignKey(Profile, verbose_name='Target', related_name='received_messages')
    timestamp = models.DateTimeField(verbose_name='Message timestamp', auto_now_add=True)
    read = models.BooleanField(verbose_name='Read')


class PrivateMessageThread(models.Model):
    messages = models.ManyToManyField(PrivateMessage, verbose_name='Messages in the thread')


class Solution(models.Model):
    url = models.CharField('URL', max_length=100, db_index=True, blank=True)
    title = models.CharField(max_length=200)
    is_public = models.BooleanField()
    publish_on = models.DateTimeField()
    content = models.TextField()
    authors = models.ManyToManyField(Profile, blank=True)

    def __unicode__(self):
        return self.title

    class Meta:
        permissions = (
            ('see_private_solution', 'See hidden solutions'),
        )


reversion.register(Profile, exclude=['points', 'last_access', 'ip', 'rating'])
reversion.register(Problem)
reversion.register(Contest, follow=['contest_problems'])
reversion.register(ContestProblem)
reversion.register(Organization)
reversion.register(BlogPost)
reversion.register(Solution)
reversion.register(Judge, fields=['name', 'created', 'auth_key', 'description'])
reversion.register(Language)
reversion.register(Comment, fields=['author', 'time', 'page', 'score', 'title', 'body', 'hidden', 'parent'])
