import itertools
import re
from collections import defaultdict, OrderedDict
from operator import itemgetter, attrgetter

import pytz
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.core.cache import cache
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Max, F, QuerySet
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _, pgettext
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from reversion import revisions
from reversion.models import Version
from sortedm2m.fields import SortedManyToManyField
from timedelta.fields import TimedeltaField

from judge.fulltext import SearchManager, SearchQuerySet
from judge.judgeapi import judge_submission, abort_submission
from judge.model_choices import ACE_THEMES
from judge.user_translations import ugettext as user_ugettext
from judge.utils.raw_sql import RawSQLColumn, unique_together_left_join


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


class RuntimeVersion(models.Model):
    language = models.ForeignKey('Language', verbose_name=_('language to which this runtime belongs'))
    judge = models.ForeignKey('Judge', verbose_name=_('judge on which this runtime exists'))
    name = models.CharField(max_length=64, verbose_name=_('runtime name'))
    version = models.CharField(max_length=64, verbose_name=_('runtime version'), blank=True)
    priority = models.IntegerField(verbose_name=_('order in which to display this runtime'), default=0)


class Language(models.Model):
    key = models.CharField(max_length=6, verbose_name=_('short identifier'),
                           help_text=_('The identifier for this language; the same as its executor id for judges.'),
                           unique=True)
    name = models.CharField(max_length=20, verbose_name=_('long name'),
                            help_text=_('Longer name for the language, e.g. "Python 2" or "C++11".'))
    short_name = models.CharField(max_length=10, verbose_name=_('short name'),
                                  help_text=_('More readable, but short, name to display publicly; e.g. "PY2" or '
                                              '"C++11". If left blank, it will default to the '
                                              'short identifier.'),
                                  null=True, blank=True)
    common_name = models.CharField(max_length=10, verbose_name=_('common name'),
                                   help_text=_('Common name for the language. For example, the common name for C++03, '
                                               'C++11, and C++14 would be "C++"'))
    ace = models.CharField(max_length=20, verbose_name=_('ace mode name'),
                           help_text=_('Language ID for Ace.js editor highlighting, appended to "mode-" to determine '
                                       'the Ace JavaScript file to use, e.g., "python".'))
    pygments = models.CharField(max_length=20, verbose_name=_('pygments name'),
                                help_text=_('Language ID for Pygments highlighting in source windows.'))
    info = models.CharField(max_length=50, verbose_name=_('runtime info override'), blank=True,
                            help_text=_("Do not set this unless you know what you're doing! It will override the "
                                        "usually more specific, judge-provided runtime info!"))
    description = models.TextField(verbose_name=_('language description'),
                                   help_text=_('Use field this to inform users of quirks with your environment, '
                                               'additional restrictions, etc.'), blank=True)
    extension = models.CharField(max_length=10, verbose_name=_('extension'),
                                 help_text=_('The extension of source files, e.g., "py" or "cpp".'))

    def runtime_versions(self):
        runtimes = OrderedDict()
        # There be dragons here if two judges specify different priorities
        for runtime in self.runtimeversion_set.all():
            id = runtime.name
            if id not in runtimes:
                runtimes[id] = set()
            if not runtime.version:  # empty str == error determining version on judge side
                continue
            runtimes[id].add(runtime.version)

        lang_versions = []
        for id, version_list in runtimes.iteritems():
            lang_versions.append((id, list(sorted(version_list, key=lambda a: tuple(map(int, a.split('.')))))))
        return lang_versions

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

    def get_absolute_url(self):
        return reverse('runtime_info', args=(self.key,))

    class Meta:
        ordering = ['key']
        verbose_name = _('language')
        verbose_name_plural = _('languages')


class Organization(models.Model):
    name = models.CharField(max_length=50, verbose_name=_('organization title'))
    key = models.CharField(max_length=6, verbose_name=_('identifier'), unique=True,
                           help_text=_('Organization name shows in URL'),
                           validators=[RegexValidator('^[A-Za-z0-9]+$',
                                                      'Identifier must contain letters and numbers only')])
    short_name = models.CharField(max_length=20, verbose_name=_('short name'),
                                  help_text=_('Displayed beside user name during contests'))
    about = models.TextField(verbose_name=_('organization description'))
    registrant = models.ForeignKey('Profile', verbose_name=_('registrant'),
                                   related_name='registrant+',
                                   help_text=_('User who registered this organization'))
    admins = models.ManyToManyField('Profile', verbose_name=_('administrators'), related_name='+',
                                    help_text=_('Those who can edit this organization'))
    creation_date = models.DateTimeField(verbose_name=_('creation date'), auto_now_add=True)
    is_open = models.BooleanField(help_text=_('Allow joining organization'), default=True)

    def __contains__(self, item):
        if isinstance(item, (int, long)):
            return self.members.filter(id=item).exists()
        elif isinstance(item, Profile):
            return self.members.filter(id=item.id).exists()
        else:
            raise TypeError('Organization membership test must be Profile or primany key')

    def __unicode__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()

    def get_absolute_url(self):
        return reverse('organization_home', args=(self.key,))

    class Meta:
        ordering = ['key']
        permissions = (
            ('organization_admin', 'Administer organizations'),
            ('edit_all_organization', 'Edit all organizations'),
        )
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')


class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name=_('user associated'))
    name = models.CharField(max_length=50, verbose_name=_('display name'), null=True, blank=True)
    about = models.TextField(verbose_name=_('self-description'), null=True, blank=True)
    timezone = models.CharField(max_length=50, verbose_name=_('location'), choices=TIMEZONE,
                                default=getattr(settings, 'DEFAULT_USER_TIME_ZONE', 'America/Toronto'))
    language = models.ForeignKey(Language, verbose_name=_('preferred language'))
    points = models.FloatField(default=0, db_index=True)
    ace_theme = models.CharField(max_length=30, choices=ACE_THEMES, default='github')
    last_access = models.DateTimeField(verbose_name=_('last access time'), default=now)
    ip = models.GenericIPAddressField(verbose_name=_('last IP'), blank=True, null=True)
    organizations = SortedManyToManyField(Organization, verbose_name=_('organization'), blank=True,
                                          related_name='members', related_query_name='member')
    display_rank = models.CharField(max_length=10, default='user', verbose_name=_('display rank'),
                                    choices=(('user', 'Normal User'), ('setter', 'Problem Setter'), ('admin', 'Admin')))
    mute = models.BooleanField(verbose_name=_('comment mute'), help_text=_('Some users are at their best when silent.'),
                               default=False)
    rating = models.IntegerField(null=True, default=None)
    user_script = models.TextField(verbose_name=_('user script'), default='', blank=True, max_length=65536,
                                   help_text=_('User-defined JavaScript for site customization.'))
    current_contest = models.OneToOneField('ContestParticipation', verbose_name=_('current contest'),
                                           null=True, blank=True, related_name='+', on_delete=models.SET_NULL)

    @cached_property
    def organization(self):
        # We do this to take advantage of prefetch_related
        orgs = self.organizations.all()
        return orgs[0] if orgs else None

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
            return pgettext('user display name', '%(username)s (%(display)s)') % {
                'username': self.user.username, 'display': self.name
            }
        return self.user.username

    @cached_property
    def solved_problems(self):
        return Submission.objects.filter(user_id=self.id, points__gt=0, problem__is_public=True).values(
            'problem').distinct().count()

    def update_contest(self):
        contest = self.current_contest
        if contest is not None and contest.ended:
            self.current_contest = None
            self.save()

    def get_absolute_url(self):
        return reverse('user_page', args=(self.user.username,))

    def __unicode__(self):
        # return u'Profile of %s in %s speaking %s' % (self.long_display_name(), self.timezone, self.language)
        return self.long_display_name

    class Meta:
        permissions = (
            ('test_site', 'Shows in-progress development stuff'),
        )
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')


class OrganizationRequest(models.Model):
    user = models.ForeignKey(Profile, verbose_name=_('user'), related_name='requests')
    organization = models.ForeignKey(Organization, verbose_name=_('organization'), related_name='requests')
    time = models.DateTimeField(verbose_name=_('request time'), auto_now_add=True)
    state = models.CharField(max_length=1, verbose_name=_('state'), choices=(
        ('P', 'Pending'),
        ('A', 'Approved'),
        ('R', 'Rejected'),
    ))
    reason = models.TextField(verbose_name=_('reason'))

    class Meta:
        verbose_name = _('organization join request')
        verbose_name_plural = _('organization join requests')


class ProblemType(models.Model):
    name = models.CharField(max_length=20, verbose_name=_('problem category ID'), unique=True)
    full_name = models.CharField(max_length=100, verbose_name=_('problem category name'))

    def __unicode__(self):
        return self.full_name

    class Meta:
        ordering = ['full_name']
        verbose_name = _('problem type')
        verbose_name_plural = _('problem types')


class ProblemGroup(models.Model):
    name = models.CharField(max_length=20, verbose_name=_('problem group ID'), unique=True)
    full_name = models.CharField(max_length=100, verbose_name=_('problem group name'))

    def __unicode__(self):
        return self.full_name

    class Meta:
        ordering = ['full_name']
        verbose_name = _('problem group')
        verbose_name_plural = _('problem groups')


class License(models.Model):
    key = models.CharField(max_length=20, unique=True, verbose_name=_('key'),
                           validators=[RegexValidator(r'^[-\w.]+$', r'License key must be ^[-\w.]+$')])
    link = models.CharField(max_length=256, verbose_name=_('link'))
    name = models.CharField(max_length=256, verbose_name=_('full name'))
    display = models.CharField(max_length=256, blank=True, verbose_name=_('short name'),
                               help_text=_('Displayed on pages under this license'))
    icon = models.CharField(max_length=256, blank=True, verbose_name=_('icon'), help_text=_('URL to the icon'))
    text = models.TextField(verbose_name=_('license text'))

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('license', args=(self.key,))

    class Meta:
        verbose_name = _('license')
        verbose_name_plural = _('licenses')


class TranslatedProblemQuerySet(SearchQuerySet):
    def __init__(self, **kwargs):
        super(TranslatedProblemQuerySet, self).__init__(('code', 'name', 'description'), **kwargs)

    def add_i18n_name(self, language):
        queryset = self.annotate(i18n_name=Coalesce(RawSQLColumn(ProblemTranslation, 'name'), F('name'),
                                                    output_field=models.CharField()))
        unique_together_left_join(queryset, ProblemTranslation, 'problem', 'language', language)
        return queryset


class TranslatedProblemForeignKeyQuerySet(QuerySet):
    def add_problem_i18n_name(self, key, language, name_field=None):
        # You must specify name_field if Problem is not yet joined into the QuerySet.
        kwargs = {key: Coalesce(RawSQLColumn(ProblemTranslation, 'name'),
                                F(name_field) if name_field else RawSQLColumn(Problem, 'name'),
                                output_field=models.CharField())}
        queryset = self.annotate(**kwargs)
        unique_together_left_join(queryset, ProblemTranslation, 'problem', 'language', language, parent_model=Problem)
        return queryset


class Problem(models.Model):
    code = models.CharField(max_length=20, verbose_name=_('problem code'), unique=True,
                            validators=[RegexValidator('^[a-z0-9]+$', _('Problem code must be ^[a-z0-9]+$'))])
    name = models.CharField(max_length=100, verbose_name=_('problem name'), db_index=True)
    description = models.TextField(verbose_name=_('problem body'))
    authors = models.ManyToManyField(Profile, verbose_name=_('creators'), blank=True, related_name='authored_problems')
    types = models.ManyToManyField(ProblemType, verbose_name=_('problem types'))
    group = models.ForeignKey(ProblemGroup, verbose_name=_('problem group'))
    time_limit = models.FloatField(verbose_name=_('time limit'))
    memory_limit = models.IntegerField(verbose_name=_('memory limit'))
    short_circuit = models.BooleanField(default=False)
    points = models.FloatField(verbose_name=_('points'))
    partial = models.BooleanField(verbose_name=_('allows partial points'), default=False)
    allowed_languages = models.ManyToManyField(Language, verbose_name=_('allowed languages'))
    is_public = models.BooleanField(verbose_name=_('publicly visible'), db_index=True, default=False)
    date = models.DateTimeField(verbose_name=_('date of publishing'), null=True, blank=True, db_index=True,
                                help_text="Doesn't have magic ability to auto-publish due to backward compatibility")
    banned_users = models.ManyToManyField(Profile, verbose_name=_('personae non gratae'), blank=True,
                                          help_text=_('Bans the selected users from submitting to this problem'))
    license = models.ForeignKey(License, null=True, blank=True, on_delete=models.SET_NULL)

    objects = TranslatedProblemQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super(Problem, self).__init__(*args, **kwargs)
        self._translated_name_cache = {}

    @cached_property
    def types_list(self):
        return map(user_ugettext, map(attrgetter('full_name'), self.types.all()))

    def languages_list(self):
        return self.allowed_languages.values_list('common_name', flat=True).distinct().order_by('common_name')

    def is_accessible_by(self, user):
        # All users can see public problems
        if self.is_public:
            return True

        # If the user can view all problems
        if user.has_perm('judge.see_private_problem'):
            return True

        # If the user authored the problem
        if user.has_perm('judge.edit_own_problem') and self.authors.filter(id=user.profile.id).exists():
            return True

        # If the user is in a contest containing that problem
        if user.is_authenticated():
            return Problem.objects.filter(id=self.id, contest__users__user=user.profile).exists()
        else:
            return False

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('problem_detail', args=(self.code,))

    @cached_property
    def author_ids(self):
        return self.authors.values_list('id', flat=True)

    @cached_property
    def usable_common_names(self):
        return set(self.usable_languages.values_list('common_name', flat=True))

    @property
    def usable_languages(self):
        return self.allowed_languages.filter(judges__in=self.judges.filter(online=True)).distinct()

    def translated_name(self, language):
        if language in self._translated_name_cache:
            return self._translated_name_cache[language]
        # Hits database despite prefetch_related.
        try:
            name = self.translations.filter(language=language).values_list('name', flat=True)[0]
        except IndexError:
            name = self.name
        self._translated_name_cache[language] = name
        return name

    class Meta:
        permissions = (
            ('see_private_problem', 'See hidden problems'),
            ('edit_own_problem', 'Edit own problems'),
            ('edit_all_problem', 'Edit all problems'),
            ('edit_public_problem', 'Edit all public problems'),
            ('clone_problem', 'Clone problem'),
            ('change_public_visibility', 'Change is_public field'),
        )
        verbose_name = _('problem')
        verbose_name_plural = _('problems')


class LanguageLimit(models.Model):
    problem = models.ForeignKey(Problem, verbose_name=_('problem'), related_name='language_limits')
    language = models.ForeignKey(Language, verbose_name=_('language'))
    time_limit = models.FloatField(verbose_name=_('time limit'))
    memory_limit = models.IntegerField(verbose_name=_('memory limit'))

    class Meta:
        unique_together = ('problem', 'language')
        verbose_name = _('language-specific resource limit')
        verbose_name_plural = _('language-specific resource limits')


class ProblemTranslation(models.Model):
    problem = models.ForeignKey(Problem, verbose_name=_('problem'), related_name='translations')
    language = models.CharField(verbose_name=_('language'), max_length=7, choices=settings.LANGUAGES)
    name = models.CharField(verbose_name=_('translated name'), max_length=100, db_index=True)
    description = models.TextField(verbose_name=_('translated description'))

    class Meta:
        unique_together = ('problem', 'language')
        verbose_name = _('problem translation')
        verbose_name_plural = _('problem translations')


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
    date = models.DateTimeField(verbose_name=_('submission time'), auto_now_add=True)
    time = models.FloatField(verbose_name=_('execution time'), null=True, db_index=True)
    memory = models.FloatField(verbose_name=_('memory usage'), null=True)
    points = models.FloatField(verbose_name=_('points granted'), null=True, db_index=True)
    language = models.ForeignKey(Language, verbose_name=_('submission language'))
    source = models.TextField(verbose_name=_('source code'), max_length=65536)
    status = models.CharField(max_length=2, choices=STATUS, default='QU', db_index=True)
    result = models.CharField(max_length=3, choices=SUBMISSION_RESULT, default=None, null=True,
                              blank=True, db_index=True)
    error = models.TextField(verbose_name=_('compile errors'), null=True, blank=True)
    current_testcase = models.IntegerField(default=0)
    batch = models.BooleanField(verbose_name=_('batched cases'), default=False)
    case_points = models.FloatField(verbose_name=_('test case points'), default=0)
    case_total = models.FloatField(verbose_name=_('test case total points'), default=0)
    judged_on = models.ForeignKey('Judge', verbose_name=_('judged on'), null=True, blank=True,
                                  on_delete=models.SET_NULL)
    is_being_rejudged = models.BooleanField(verbose_name=_('is being rejudged by admin'), default=False)
    is_pretested = models.BooleanField(verbose_name=_('was ran on pretests only'), default=False)

    objects = TranslatedProblemForeignKeyQuerySet.as_manager()

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
        judge_submission(self)

    judge.alters_data = True

    def abort(self):
        abort_submission(self)

    abort.alters_data = True

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


class Comment(MPTTModel):
    author = models.ForeignKey(Profile, verbose_name=_('commenter'))
    time = models.DateTimeField(verbose_name=_('posted time'), auto_now_add=True)
    page = models.CharField(max_length=30, verbose_name=_('associated Page'), db_index=True,
                            validators=[RegexValidator('^[pc]:[a-z0-9]+$|^b:\d+$|^s:',
                                                       _('Page code must be ^[pc]:[a-z0-9]+$|^b:\d+$'))])
    score = models.IntegerField(verbose_name=_('votes'), default=0)
    title = models.CharField(max_length=200, verbose_name=_('title of comment'))
    body = models.TextField(verbose_name=_('body of comment'))
    hidden = models.BooleanField(verbose_name=_('hide the comment'), default=0)
    parent = TreeForeignKey('self', verbose_name=_('parent'), null=True, blank=True, related_name='replies')
    versions = GenericRelation(Version, object_id_field='object_id_int')

    class Meta:
        verbose_name = _('comment')
        verbose_name_plural = _('comments')

    class MPTTMeta:
        order_insertion_by = ['-time']

    @classmethod
    def most_recent(cls, user, n, batch=None):
        queryset = cls.objects.filter(hidden=False).select_related('author__user')\
            .defer('author__about', 'body').order_by('-id')
        if user.is_superuser:
            return queryset[:n]
        if batch is None:
            batch = 2 * n
        output = []
        for i in itertools.count(0):
            slice = queryset[i * batch:i * batch + batch]
            if not slice:
                break
            for comment in slice:
                if comment.page.startswith('p:'):
                    if Problem.objects.get(code=comment.page[2:]).is_accessible_by(user):
                        output.append(comment)
                else:
                    output.append(comment)
                if len(output) >= n:
                    return output
        return output

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
        return '%s#comment-%d' % (self.link, self.id)

    def __unicode__(self):
        return self.title

        # Only use this when queried with
        # .prefetch_related(Prefetch('votes', queryset=CommentVote.objects.filter(voter_id=profile_id)))
        # It's rather stupid to put a query specific property on the model, but the alternative requires
        # digging Django internals, and could not be guaranteed to work forever.
        # Hence it is left here for when the alternative breaks.
        # @property
        # def vote_score(self):
        #    queryset = self.votes.all()
        #    if not queryset:
        #        return 0
        #    return queryset[0].score


class CommentVote(models.Model):
    voter = models.ForeignKey(Profile, related_name='voted_comments')
    comment = models.ForeignKey(Comment, related_name='votes')
    score = models.IntegerField()

    class Meta:
        unique_together = ['voter', 'comment']
        verbose_name = _('comment vote')
        verbose_name_plural = _('comment votes')


class MiscConfig(models.Model):
    key = models.CharField(max_length=30, db_index=True)
    value = models.TextField(blank=True)

    def __unicode__(self):
        return self.key

    class Meta:
        verbose_name = _('configuration item')
        verbose_name_plural = _('miscellaneous configuration')


def validate_regex(regex):
    try:
        re.compile(regex, re.VERBOSE)
    except re.error as e:
        raise ValidationError('Invalid regex: %s' % e.message)


class NavigationBar(MPTTModel):
    class Meta:
        verbose_name = _('navigation item')
        verbose_name_plural = _('navigation bar')

    class MPTTMeta:
        order_insertion_by = ['order']

    order = models.PositiveIntegerField(db_index=True, verbose_name=_('order'))
    key = models.CharField(max_length=10, unique=True, verbose_name=_('identifier'))
    label = models.CharField(max_length=20, verbose_name=_('label'))
    path = models.CharField(max_length=255, verbose_name=_('link path'))
    regex = models.TextField(verbose_name=_('highlight regex'), validators=[validate_regex])
    parent = TreeForeignKey('self', verbose_name=_('parent item'), null=True, blank=True, related_name='children')

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
    name = models.CharField(max_length=50, help_text=_('Server name, hostname-style'), unique=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('time of creation'))
    auth_key = models.CharField(max_length=100, help_text=_('A key to authenticated this judge'),
                                verbose_name=_('authentication key'))
    online = models.BooleanField(verbose_name=_('judge online status'), default=False)
    start_time = models.DateTimeField(verbose_name=_('judge start time'), null=True)
    ping = models.FloatField(verbose_name=_('response time'), null=True)
    load = models.FloatField(verbose_name=_('system load'), null=True,
                             help_text=_('Load for the last minute, divided by processors to be fair.'))
    description = models.TextField(blank=True, verbose_name=_('description'))
    last_ip = models.GenericIPAddressField(verbose_name='Last connected IP', blank=True, null=True)
    problems = models.ManyToManyField(Problem, verbose_name=_('problems'), related_name='judges')
    runtimes = models.ManyToManyField(Language, verbose_name=_('judges'), related_name='judges')

    def __unicode__(self):
        return self.name

    @cached_property
    def runtime_versions(self):
        qs = (self.runtimeversion_set.values('language__key', 'language__name', 'version', 'name')
                  .order_by('language__key', 'priority'))

        ret = OrderedDict()

        for data in qs:
            key = data['language__key']
            if key not in ret:
                ret[key] = {'name': data['language__name'], 'runtime': []}
            ret[key]['runtime'].append((data['name'], (data['version'],)))

        return ret.items()

    @cached_property
    def uptime(self):
        return timezone.now() - self.start_time if self.online else 'N/A'

    @cached_property
    def ping_ms(self):
        return self.ping * 1000

    @cached_property
    def runtime_list(self):
        return map(attrgetter('name'), self.runtimes.all())

    class Meta:
        ordering = ['name']
        verbose_name = _('judge')
        verbose_name_plural = _('judges')


class ContestTag(models.Model):
    color_validator = RegexValidator('^#(?:[A-Fa-f0-9]{3}){1,2}$', _('Invalid colour.'))

    name = models.CharField(max_length=20, verbose_name=_('tag name'), unique=True,
                            validators=[RegexValidator(r'^[a-z-]+$', message=_('Lowercase letters and hyphens only.'))])
    color = models.CharField(max_length=7, verbose_name=_('tag colour'), validators=[color_validator])
    description = models.TextField(verbose_name=_('tag description'), blank=True)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('contest_tag', args=[self.name])

    @property
    def text_color(self, cache={}):
        if self.color not in cache:
            if len(self.color) == 4:
                r, g, b = [ord((i * 2).decode('hex')) for i in self.color[1:]]
            else:
                r, g, b = [ord(i) for i in self.color[1:].decode('hex')]
            cache[self.color] = '#000' if 299 * r + 587 * g + 144 * b > 140000 else '#fff'
        return cache[self.color]

    class Meta:
        verbose_name = _('contest tag')
        verbose_name_plural = _('contest tags')


class Contest(models.Model):
    key = models.CharField(max_length=20, verbose_name=_('contest id'), unique=True,
                           validators=[RegexValidator('^[a-z0-9]+$', _('Contest id must be ^[a-z0-9]+$'))])
    name = models.CharField(max_length=100, verbose_name=_('contest name'), db_index=True)
    organizers = models.ManyToManyField(Profile, help_text=_('These people will be able to edit the contest.'),
                                        related_name='organizers+')
    description = models.TextField(blank=True)
    problems = models.ManyToManyField(Problem, verbose_name=_('problems'), through='ContestProblem')
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    time_limit = TimedeltaField(verbose_name=_('time limit'), blank=True, null=True)
    is_public = models.BooleanField(verbose_name=_('publicly visible'), default=False,
                                    help_text=_('Should be set even for organization-private contests, where it '
                                                'determines whether the contest is visible to members of the '
                                                'specified organizations.'))
    is_external = models.BooleanField(verbose_name=_('external contest'), default=False)
    is_rated = models.BooleanField(verbose_name=_('contest rated'), help_text=_('Whether this contest can be rated.'),
                                   default=False)
    rate_all = models.BooleanField(verbose_name=_('rate all'), help_text=_('Rate all users who joined.'), default=False)
    rate_exclude = models.ManyToManyField(Profile, verbose_name=_('exclude from ratings'), blank=True,
                                          related_name='rate_exclude+')
    is_private = models.BooleanField(verbose_name=_('private to organizations'), default=False)
    hide_problem_tags = models.BooleanField(verbose_name=_('hide problem tags'),
                                            help_text=_('Whether problem tags should be hidden by default.'),
                                            default=False)
    run_pretests_only = models.BooleanField(verbose_name=_('run pretests only'),
                                            help_text=_('Whether judges should grade pretests only, versus all '
                                                        'testcases. Commonly set during a contest, then unset '
                                                        'prior to rejudging user submissions when the contest ends.'),
                                            default=False)
    organizations = models.ManyToManyField(Organization, blank=True, verbose_name=_('organizations'),
                                           help_text=_('If private, only these organizations may see the contest'))
    og_image = models.CharField(verbose_name=_('OpenGraph image'), default='', max_length=150, blank=True)
    tags = models.ManyToManyField(ContestTag, verbose_name=_('contest tags'), blank=True, related_name='contests')

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError('What is this? A contest that ended before it starts?')

    @property
    def contest_window_length(self):
        return self.end_time - self.start_time

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
        verbose_name = _('contest')
        verbose_name_plural = _('contests')


class ContestParticipation(models.Model):
    contest = models.ForeignKey(Contest, verbose_name=_('associated contest'), related_name='users')
    user = models.ForeignKey(Profile, verbose_name=_('user'), related_name='contest_history')
    real_start = models.DateTimeField(verbose_name=_('start time'), default=timezone.now, db_column='start')
    score = models.IntegerField(verbose_name=_('score'), default=0, db_index=True)
    cumtime = models.PositiveIntegerField(verbose_name=_('cumulative time'), default=0)

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
        return contest.end_time if contest.time_limit is None else \
            min(self.real_start + contest.time_limit, contest.end_time)

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
        for problem in self.contest.contest_problems.all():
            solution = problem.submissions.filter(submission__user_id=self.user_id, points__gt=0)\
                .values('submission__user_id').annotate(time=Max('submission__date'))
            if not solution:
                continue
            dt = solution[0]['time'] - self.start
            cumtime += dt.days * 86400 + dt.seconds
        self.cumtime = cumtime
        self.save()

    def __unicode__(self):
        return '%s in %s' % (self.user.long_display_name, self.contest.name)

    class Meta:
        verbose_name = _('contest participation')
        verbose_name_plural = _('contest participations')


class ContestProblem(models.Model):
    problem = models.ForeignKey(Problem, verbose_name=_('problem'), related_name='contests')
    contest = models.ForeignKey(Contest, verbose_name=_('contest'), related_name='contest_problems')
    points = models.IntegerField(verbose_name=_('points'))
    partial = models.BooleanField(default=True, verbose_name=_('partial'))
    order = models.PositiveIntegerField(db_index=True, verbose_name=_('order'))
    output_prefix_override = models.IntegerField(verbose_name=_('output prefix length override'), null=True, blank=True)

    class Meta:
        unique_together = ('problem', 'contest')
        verbose_name = _('contest problem')
        verbose_name_plural = _('contest problems')


class ContestSubmission(models.Model):
    submission = models.OneToOneField(Submission, verbose_name=_('submission'), related_name='contest')
    problem = models.ForeignKey(ContestProblem, verbose_name=_('problem'),
                                related_name='submissions', related_query_name='submission')
    participation = models.ForeignKey(ContestParticipation, verbose_name=_('participation'),
                                      related_name='submissions', related_query_name='submission')
    points = models.FloatField(default=0.0, verbose_name=_('points'))
    is_pretest = models.BooleanField(verbose_name=_('is pretested'),
                                     help_text=_('Whether this submission was ran only on pretests.'),
                                     default=False)

    class Meta:
        verbose_name = _('contest submission')
        verbose_name_plural = _('contest submissions')


class Rating(models.Model):
    user = models.ForeignKey(Profile, verbose_name=_('user'), related_name='ratings')
    contest = models.ForeignKey(Contest, verbose_name=_('contest'), related_name='ratings')
    participation = models.OneToOneField(ContestParticipation, verbose_name=_('participation'), related_name='rating')
    rank = models.IntegerField(verbose_name=_('rank'))
    rating = models.IntegerField(verbose_name=_('rating'))
    volatility = models.IntegerField(verbose_name=_('volatility'))
    last_rated = models.DateTimeField(db_index=True, verbose_name=_('last rated'))

    class Meta:
        unique_together = ('user', 'contest')
        verbose_name = _('contest rating')
        verbose_name_plural = _('contest ratings')


class BlogPost(models.Model):
    title = models.CharField(verbose_name=_('post title'), max_length=100)
    slug = models.SlugField(verbose_name=_('slug'))
    visible = models.BooleanField(verbose_name=_('public visibility'), default=False)
    sticky = models.BooleanField(verbose_name=_('sticky'), default=False)
    publish_on = models.DateTimeField(verbose_name=_('publish after'))
    content = models.TextField(verbose_name=_('post content'))
    summary = models.TextField(verbose_name=_('post summary'), blank=True)
    og_image = models.CharField(verbose_name=_('openGraph image'), default='', max_length=150, blank=True)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog_post', args=(self.id, self.slug))

    class Meta:
        permissions = (
            ('see_hidden_post', 'See hidden posts'),
        )
        verbose_name = _('blog post')
        verbose_name_plural = _('blog posts')


class PrivateMessage(models.Model):
    title = models.CharField(verbose_name=_('message title'), max_length=50)
    content = models.TextField(verbose_name=_('message body'))
    sender = models.ForeignKey(Profile, verbose_name=_('sender'), related_name='sent_messages')
    target = models.ForeignKey(Profile, verbose_name=_('target'), related_name='received_messages')
    timestamp = models.DateTimeField(verbose_name=_('message timestamp'), auto_now_add=True)
    read = models.BooleanField(verbose_name=_('read'), default=False)


class PrivateMessageThread(models.Model):
    messages = models.ManyToManyField(PrivateMessage, verbose_name=_('messages in the thread'))


class Solution(models.Model):
    url = models.CharField('URL', max_length=100, db_index=True, blank=True)
    title = models.CharField(max_length=200)
    is_public = models.BooleanField(default=False)
    publish_on = models.DateTimeField()
    content = models.TextField()
    authors = models.ManyToManyField(Profile, blank=True)
    problem = models.ForeignKey(Problem, on_delete=models.SET_NULL, verbose_name=_('associated problem'),
                                null=True, blank=True)

    def get_absolute_url(self):
        return reverse('solution', args=[self.url])

    def __unicode__(self):
        return self.title

    class Meta:
        permissions = (
            ('see_private_solution', 'See hidden solutions'),
        )
        verbose_name = _('solution')
        verbose_name_plural = _('solutions')


revisions.register(Profile, exclude=['points', 'last_access', 'ip', 'rating'])
revisions.register(Problem, follow=['language_limits'])
revisions.register(LanguageLimit)
revisions.register(Contest, follow=['contest_problems'])
revisions.register(ContestProblem)
revisions.register(Organization)
revisions.register(BlogPost)
revisions.register(Solution)
revisions.register(Judge, fields=['name', 'created', 'auth_key', 'description'])
revisions.register(Language)
revisions.register(Comment, fields=['author', 'time', 'page', 'score', 'title', 'body', 'hidden', 'parent'])
