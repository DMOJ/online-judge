from enum import IntEnum
from operator import attrgetter

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import CASCADE, Exists, F, FilteredRelation, OuterRef, Q, SET_NULL
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from judge.fulltext import SearchQuerySet
from judge.models.profile import Organization, Profile
from judge.models.runtime import Language
from judge.user_translations import gettext as user_gettext

__all__ = ['ProblemGroup', 'ProblemType', 'Problem', 'ProblemTranslation', 'ProblemClarification', 'License',
           'Solution', 'SubmissionSourceAccess', 'TranslatedProblemQuerySet']


def disallowed_characters_validator(text):
    common_disallowed_characters = set(text) & settings.DMOJ_PROBLEM_STATEMENT_DISALLOWED_CHARACTERS
    if common_disallowed_characters:
        raise ValidationError(_('Disallowed characters: %(value)s'),
                              params={'value': ''.join(common_disallowed_characters)})


class ProblemType(models.Model):
    name = models.CharField(max_length=20, verbose_name=_('problem category ID'), unique=True)
    full_name = models.CharField(max_length=100, verbose_name=_('problem category name'))

    def __str__(self):
        return self.full_name

    class Meta:
        ordering = ['full_name']
        verbose_name = _('problem type')
        verbose_name_plural = _('problem types')


class ProblemGroup(models.Model):
    name = models.CharField(max_length=20, verbose_name=_('problem group ID'), unique=True)
    full_name = models.CharField(max_length=100, verbose_name=_('problem group name'))

    def __str__(self):
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
                               help_text=_('Displayed on pages under this license.'))
    icon = models.CharField(max_length=256, blank=True, verbose_name=_('icon'), help_text=_('URL to the icon.'))
    text = models.TextField(verbose_name=_('license text'))

    def __str__(self):
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
        return self.annotate(i18n_translation=FilteredRelation(
            'translations', condition=Q(translations__language=language),
        )).annotate(i18n_name=Coalesce(F('i18n_translation__name'), F('name'), output_field=models.CharField()))


class SubmissionSourceAccess:
    ALWAYS = 'A'
    SOLVED = 'S'
    ONLY_OWN = 'O'
    FOLLOW = 'F'


class VotePermission(IntEnum):
    NONE = 0
    VIEW = 1
    VOTE = 2

    def can_view(self):
        return self >= VotePermission.VIEW

    def can_vote(self):
        return self >= VotePermission.VOTE


class Problem(models.Model):
    SUBMISSION_SOURCE_ACCESS = (
        (SubmissionSourceAccess.FOLLOW, _('Follow global setting')),
        (SubmissionSourceAccess.ALWAYS, _('Always visible')),
        (SubmissionSourceAccess.SOLVED, _('Visible if problem solved')),
        (SubmissionSourceAccess.ONLY_OWN, _('Only own submissions')),
    )

    code = models.CharField(max_length=20, verbose_name=_('problem code'), unique=True,
                            validators=[RegexValidator('^[a-z0-9]+$', _('Problem code must be ^[a-z0-9]+$'))],
                            help_text=_('A short, unique code for the problem, used in the URL after /problem/'))
    name = models.CharField(max_length=100, verbose_name=_('problem name'), db_index=True,
                            help_text=_('The full name of the problem, as shown in the problem list.'),
                            validators=[disallowed_characters_validator])
    description = models.TextField(verbose_name=_('problem body'), validators=[disallowed_characters_validator])
    authors = models.ManyToManyField(Profile, verbose_name=_('creators'), blank=True, related_name='authored_problems',
                                     help_text=_('These users will be able to edit the problem, '
                                                 'and be listed as authors.'))
    curators = models.ManyToManyField(Profile, verbose_name=_('curators'), blank=True, related_name='curated_problems',
                                      help_text=_('These users will be able to edit the problem, '
                                                  'but not be listed as authors.'))
    testers = models.ManyToManyField(Profile, verbose_name=_('testers'), blank=True, related_name='tested_problems',
                                     help_text=_(
                                         'These users will be able to view the private problem, but not edit it.'))
    types = models.ManyToManyField(ProblemType, verbose_name=_('problem types'),
                                   help_text=_("The type of problem, as shown on the problem's page."))
    group = models.ForeignKey(ProblemGroup, verbose_name=_('problem group'), on_delete=CASCADE,
                              help_text=_('The group of problem, shown under Category in the problem list.'))
    time_limit = models.FloatField(verbose_name=_('time limit'),
                                   help_text=_('The time limit for this problem, in seconds. '
                                               'Fractional seconds (e.g. 1.5) are supported.'),
                                   validators=[MinValueValidator(settings.DMOJ_PROBLEM_MIN_TIME_LIMIT),
                                               MaxValueValidator(settings.DMOJ_PROBLEM_MAX_TIME_LIMIT)])
    memory_limit = models.PositiveIntegerField(verbose_name=_('memory limit'),
                                               help_text=_('The memory limit for this problem, in kilobytes '
                                                           '(e.g. 256mb = 262144 kilobytes).'),
                                               validators=[MinValueValidator(settings.DMOJ_PROBLEM_MIN_MEMORY_LIMIT),
                                                           MaxValueValidator(settings.DMOJ_PROBLEM_MAX_MEMORY_LIMIT)])
    short_circuit = models.BooleanField(verbose_name=_('short circuit'), default=False)
    points = models.FloatField(verbose_name=_('points'),
                               help_text=_('Points awarded for problem completion. '
                                           "Points are displayed with a 'p' suffix if partial."),
                               validators=[MinValueValidator(settings.DMOJ_PROBLEM_MIN_PROBLEM_POINTS)])
    partial = models.BooleanField(verbose_name=_('allows partial points'), default=False)
    allowed_languages = models.ManyToManyField(Language, verbose_name=_('allowed languages'),
                                               help_text=_('List of allowed submission languages.'))
    is_public = models.BooleanField(verbose_name=_('publicly visible'), db_index=True, default=False)
    is_manually_managed = models.BooleanField(verbose_name=_('manually managed'), db_index=True, default=False,
                                              help_text=_('Whether judges should be allowed to manage data or not.'))
    date = models.DateTimeField(verbose_name=_('date of publishing'), null=True, blank=True, db_index=True,
                                help_text=_(
                                    "Doesn't have the magic ability to auto-publish due to backward compatibility."))
    banned_users = models.ManyToManyField(Profile, verbose_name=_('personae non gratae'), blank=True,
                                          help_text=_('Bans the selected users from submitting to this problem.'))
    license = models.ForeignKey(License, null=True, blank=True, on_delete=SET_NULL, verbose_name=_('license'),
                                help_text=_('The license under which this problem is published.'))
    og_image = models.CharField(verbose_name=_('OpenGraph image'), max_length=150, blank=True)
    summary = models.TextField(blank=True, verbose_name=_('problem summary'),
                               help_text=_('Plain-text, shown in meta description tag, e.g. for social media.'))
    user_count = models.IntegerField(verbose_name=_('number of users'), default=0,
                                     help_text=_('The number of users who solved the problem.'))
    ac_rate = models.FloatField(verbose_name=_('solve rate'), default=0)
    is_full_markup = models.BooleanField(verbose_name=_('allow full markdown access'), default=False)
    submission_source_visibility_mode = models.CharField(verbose_name=_('submission source visibility'), max_length=1,
                                                         default=SubmissionSourceAccess.FOLLOW,
                                                         choices=SUBMISSION_SOURCE_ACCESS)

    objects = TranslatedProblemQuerySet.as_manager()
    tickets = GenericRelation('Ticket')

    organizations = models.ManyToManyField(Organization, blank=True, verbose_name=_('organizations'),
                                           help_text=_('If private, only these organizations may see the problem.'))
    is_organization_private = models.BooleanField(verbose_name=_('private to organizations'), default=False)

    def __init__(self, *args, **kwargs):
        super(Problem, self).__init__(*args, **kwargs)
        self._translated_name_cache = {}
        self._i18n_name = None
        self.__original_code = self.code

    @cached_property
    def types_list(self):
        return list(map(user_gettext, map(attrgetter('full_name'), self.types.all())))

    def languages_list(self):
        return self.allowed_languages.values_list('common_name', flat=True).distinct().order_by('common_name')

    def is_editor(self, profile):
        return (self.authors.filter(id=profile.id) | self.curators.filter(id=profile.id)).exists()

    def is_editable_by(self, user):
        if not user.is_authenticated:
            return False
        if not user.has_perm('judge.edit_own_problem'):
            return False
        if user.has_perm('judge.edit_all_problem') or user.has_perm('judge.edit_public_problem') and self.is_public:
            return True
        if user.profile.id in self.editor_ids:
            return True
        if self.is_organization_private and self.organizations.filter(admins=user.profile).exists():
            return True
        return False

    def is_accessible_by(self, user, skip_contest_problem_check=False):
        # If we don't want to check if the user is in a contest containing that problem.
        if not skip_contest_problem_check and user.is_authenticated:
            # If user is currently in a contest containing that problem.
            current = user.profile.current_contest_id
            if current is not None:
                from judge.models import ContestProblem
                if ContestProblem.objects.filter(problem_id=self.id, contest__users__id=current).exists():
                    return True

        # Problem is public.
        if self.is_public:
            # Problem is not private to an organization.
            if not self.is_organization_private:
                return True

            # If the user can see all organization private problems.
            if user.has_perm('judge.see_organization_problem'):
                return True

            # If the user is in the organization.
            if user.is_authenticated and \
                    self.organizations.filter(id__in=user.profile.organizations.all()):
                return True

        if not user.is_authenticated:
            return False

        # If the user can view all problems.
        if user.has_perm('judge.see_private_problem'):
            return True

        # If the user can edit the problem.
        # We are using self.editor_ids to take advantage of caching.
        if self.is_editable_by(user) or user.profile.id in self.editor_ids:
            return True

        # If user is a tester.
        if self.testers.filter(id=user.profile.id).exists():
            return True

        return False

    def is_subs_manageable_by(self, user):
        return user.is_staff and user.has_perm('judge.rejudge_submission') and self.is_editable_by(user)

    @classmethod
    def get_visible_problems(cls, user):
        # Do unauthenticated check here so we can skip authentication checks later on.
        if not user.is_authenticated:
            return cls.get_public_problems()

        # Conditions for visible problem:
        #   - `judge.edit_all_problem` or `judge.see_private_problem`
        #   - otherwise
        #       - not is_public problems
        #           - author or curator or tester
        #           - is_organization_private and admin of organization
        #       - is_public problems
        #           - not is_organization_private or in organization or `judge.see_organization_problem`
        #           - author or curator or tester
        queryset = cls.objects.defer('description')

        edit_own_problem = user.has_perm('judge.edit_own_problem')
        edit_public_problem = edit_own_problem and user.has_perm('judge.edit_public_problem')
        edit_all_problem = edit_own_problem and user.has_perm('judge.edit_all_problem')

        if not (user.has_perm('judge.see_private_problem') or edit_all_problem):
            q = Q(is_public=True)
            if not (user.has_perm('judge.see_organization_problem') or edit_public_problem):
                # Either not organization private or in the organization.
                q &= Q(is_organization_private=False) | cls.organization_filter_q(
                    # Avoids needlessly joining Organization
                    Profile.organizations.through.objects.filter(profile=user.profile).values('organization_id'),
                )

            if edit_own_problem:
                q |= cls.organization_filter_q(
                    # Avoids needlessly joining Organization
                    Organization.admins.through.objects.filter(profile=user.profile).values('organization_id'),
                )

            # Authors, curators, and testers should always have access.
            q = cls.q_add_author_curator_tester(q, user.profile)
            queryset = queryset.filter(q)

        return queryset

    @classmethod
    def q_add_author_curator_tester(cls, q, profile):
        # This is way faster than the obvious |= Q(authors=profile) et al. because we are not doing
        # joins and forcing the user to clean it up with .distinct().
        q |= Exists(Problem.authors.through.objects.filter(problem=OuterRef('pk'), profile=profile))
        q |= Exists(Problem.curators.through.objects.filter(problem=OuterRef('pk'), profile=profile))
        q |= Exists(Problem.testers.through.objects.filter(problem=OuterRef('pk'), profile=profile))
        return q

    @classmethod
    def organization_filter_q(cls, queryset):
        q = Q(is_organization_private=True)
        q &= Exists(Problem.organizations.through.objects.filter(problem=OuterRef('pk'), organization__in=queryset))
        return q

    @classmethod
    def get_public_problems(cls):
        return cls.objects.filter(is_public=True, is_organization_private=False).defer('description')

    @classmethod
    def get_editable_problems(cls, user):
        if not user.has_perm('judge.edit_own_problem'):
            return cls.objects.none()
        if user.has_perm('judge.edit_all_problem'):
            return cls.objects.all()

        q = Q(authors=user.profile) | Q(curators=user.profile)
        q |= Q(is_organization_private=True, organizations__in=user.profile.admin_of.all())

        if user.has_perm('judge.edit_public_problem'):
            q |= Q(is_public=True)

        return cls.objects.filter(q)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('problem_detail', args=(self.code,))

    @cached_property
    def author_ids(self):
        return Problem.authors.through.objects.filter(problem=self).values_list('profile_id', flat=True)

    @cached_property
    def editor_ids(self):
        return self.author_ids.union(
            Problem.curators.through.objects.filter(problem=self).values_list('profile_id', flat=True))

    @cached_property
    def tester_ids(self):
        return Problem.testers.through.objects.filter(problem=self).values_list('profile_id', flat=True)

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

    @property
    def i18n_name(self):
        if self._i18n_name is None:
            self._i18n_name = self._trans[0].name if self._trans else self.name
        return self._i18n_name

    @i18n_name.setter
    def i18n_name(self, value):
        self._i18n_name = value

    @property
    def clarifications(self):
        return ProblemClarification.objects.filter(problem=self)

    @cached_property
    def submission_source_visibility(self):
        if self.submission_source_visibility_mode == SubmissionSourceAccess.FOLLOW:
            return {
                'all': SubmissionSourceAccess.ALWAYS,
                'all-solved': SubmissionSourceAccess.SOLVED,
                'only-own': SubmissionSourceAccess.ONLY_OWN,
            }[settings.DMOJ_SUBMISSION_SOURCE_VISIBILITY]
        return self.submission_source_visibility_mode

    def update_stats(self):
        all_queryset = self.submission_set.filter(user__is_unlisted=False)
        ac_queryset = all_queryset.filter(points__gte=self.points, result='AC')
        self.user_count = ac_queryset.values('user').distinct().count()
        submissions = all_queryset.count()
        if submissions:
            self.ac_rate = 100.0 * ac_queryset.count() / submissions
        else:
            self.ac_rate = 0
        self.save()

    update_stats.alters_data = True

    def _get_limits(self, key):
        global_limit = getattr(self, key)
        limits = {limit['language_id']: (limit['language__name'], limit[key])
                  for limit in self.language_limits.values('language_id', 'language__name', key)
                  if limit[key] != global_limit}
        limit_ids = set(limits.keys())
        common = []

        for cn, ids in Language.get_common_name_map().items():
            if ids - limit_ids:
                continue
            limit = set(limits[id][1] for id in ids)
            if len(limit) == 1:
                limit = next(iter(limit))
                common.append((cn, limit))
                for id in ids:
                    del limits[id]

        limits = list(limits.values()) + common
        limits.sort()
        return limits

    @property
    def language_time_limit(self):
        key = 'problem_tls:%d' % self.id
        result = cache.get(key)
        if result is not None:
            return result
        result = self._get_limits('time_limit')
        cache.set(key, result)
        return result

    @property
    def language_memory_limit(self):
        key = 'problem_mls:%d' % self.id
        result = cache.get(key)
        if result is not None:
            return result
        result = self._get_limits('memory_limit')
        cache.set(key, result)
        return result

    @property
    def markdown_style(self):
        return 'problem-full' if self.is_full_markup else 'problem'

    def save(self, *args, **kwargs):
        super(Problem, self).save(*args, **kwargs)
        if self.code != self.__original_code:
            try:
                problem_data = self.data_files
            except AttributeError:
                pass
            else:
                problem_data._update_code(self.__original_code, self.code)

    save.alters_data = True

    def is_solved_by(self, user):
        # Return true if a full AC submission to the problem from the user exists.
        return self.submission_set.filter(user=user.profile, result='AC', points__gte=F('problem__points')).exists()

    def vote_permission_for_user(self, user):
        if not user.is_authenticated:
            return VotePermission.NONE

        # If the user is in contest, nothing should be shown.
        if user.profile.current_contest:
            return VotePermission.NONE

        # If the user is not allowed to vote.
        if user.profile.is_unlisted or user.profile.is_banned_from_problem_voting:
            return VotePermission.VIEW

        # If the user is banned from submitting to the problem.
        if self.banned_users.filter(pk=user.pk).exists():
            return VotePermission.VIEW

        # If the user has not solved the problem.
        if not self.is_solved_by(user):
            return VotePermission.VIEW

        return VotePermission.VOTE

    class Meta:
        permissions = (
            ('see_private_problem', _('See hidden problems')),
            ('edit_own_problem', _('Edit own problems')),
            ('edit_all_problem', _('Edit all problems')),
            ('edit_public_problem', _('Edit all public problems')),
            ('problem_full_markup', _('Edit problems with full markup')),
            ('clone_problem', _('Clone problem')),
            ('change_public_visibility', _('Change is_public field')),
            ('change_manually_managed', _('Change is_manually_managed field')),
            ('see_organization_problem', _('See organization-private problems')),
        )
        verbose_name = _('problem')
        verbose_name_plural = _('problems')


class ProblemTranslation(models.Model):
    problem = models.ForeignKey(Problem, verbose_name=_('problem'), related_name='translations', on_delete=CASCADE)
    language = models.CharField(verbose_name=_('language'), max_length=7, choices=settings.LANGUAGES)
    name = models.CharField(verbose_name=_('translated name'), max_length=100, db_index=True)
    description = models.TextField(verbose_name=_('translated description'),
                                   validators=[disallowed_characters_validator])

    class Meta:
        unique_together = ('problem', 'language')
        verbose_name = _('problem translation')
        verbose_name_plural = _('problem translations')


class ProblemClarification(models.Model):
    problem = models.ForeignKey(Problem, verbose_name=_('clarified problem'), on_delete=CASCADE)
    description = models.TextField(verbose_name=_('clarification body'), validators=[disallowed_characters_validator])
    date = models.DateTimeField(verbose_name=_('clarification timestamp'), auto_now_add=True)

    class Meta:
        verbose_name = _('problem clarification')
        verbose_name_plural = _('problem clarifications')


class LanguageLimit(models.Model):
    problem = models.ForeignKey(Problem, verbose_name=_('problem'), related_name='language_limits', on_delete=CASCADE)
    language = models.ForeignKey(Language, verbose_name=_('language'), on_delete=CASCADE)
    time_limit = models.FloatField(verbose_name=_('time limit'),
                                   validators=[MinValueValidator(settings.DMOJ_PROBLEM_MIN_TIME_LIMIT),
                                               MaxValueValidator(settings.DMOJ_PROBLEM_MAX_TIME_LIMIT)])
    memory_limit = models.IntegerField(verbose_name=_('memory limit'),
                                       validators=[MinValueValidator(settings.DMOJ_PROBLEM_MIN_MEMORY_LIMIT),
                                                   MaxValueValidator(settings.DMOJ_PROBLEM_MAX_MEMORY_LIMIT)])

    class Meta:
        unique_together = ('problem', 'language')
        verbose_name = _('language-specific resource limit')
        verbose_name_plural = _('language-specific resource limits')


class Solution(models.Model):
    problem = models.OneToOneField(Problem, on_delete=CASCADE, verbose_name=_('associated problem'),
                                   blank=True, related_name='solution')
    is_public = models.BooleanField(verbose_name=_('public visibility'), default=False)
    publish_on = models.DateTimeField(verbose_name=_('publish date'))
    authors = models.ManyToManyField(Profile, verbose_name=_('authors'), blank=True)
    content = models.TextField(verbose_name=_('editorial content'), validators=[disallowed_characters_validator])

    def get_absolute_url(self):
        problem = self.problem
        if problem is None:
            return reverse('home')
        else:
            return reverse('problem_editorial', args=[problem.code])

    def __str__(self):
        return _('Editorial for %s') % self.problem.name

    def is_accessible_by(self, user):
        if self.is_public and self.publish_on < timezone.now():
            return True
        if user.has_perm('judge.see_private_solution'):
            return True
        if self.problem.is_editable_by(user):
            return True
        return False

    class Meta:
        permissions = (
            ('see_private_solution', _('See hidden solutions')),
        )
        verbose_name = _('solution')
        verbose_name_plural = _('solutions')


class ProblemPointsVote(models.Model):
    points = models.IntegerField(
        verbose_name=_('proposed points'),
        help_text=_('The amount of points the voter thinks this problem deserves.'),
        validators=[
            MinValueValidator(settings.DMOJ_PROBLEM_MIN_USER_POINTS_VOTE),
            MaxValueValidator(settings.DMOJ_PROBLEM_MAX_USER_POINTS_VOTE),
        ],
    )
    voter = models.ForeignKey(Profile, verbose_name=_('voter'), related_name='problem_points_votes', on_delete=CASCADE)
    problem = models.ForeignKey(Problem, verbose_name=_('problem'), related_name='problem_points_votes',
                                on_delete=CASCADE)
    vote_time = models.DateTimeField(verbose_name=_('vote time'), help_text=_('The time this vote was cast.'),
                                     auto_now_add=True)
    note = models.TextField(verbose_name=_('note'), help_text=_('Justification for problem point value.'),
                            max_length=8192, blank=True, default='')

    class Meta:
        verbose_name = _('problem vote')
        verbose_name_plural = _('problem votes')

    def __str__(self):
        return _('Points vote by %(voter)s for %(problem)s') % {'voter': self.voter, 'problem': self.problem}
