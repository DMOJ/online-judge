from operator import attrgetter

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, QuerySet
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from judge.fulltext import SearchQuerySet
from judge.models.profile import Profile
from judge.models.runtime import Language
from judge.user_translations import ugettext as user_ugettext
from judge.utils.raw_sql import unique_together_left_join, RawSQLColumn

__all__ = ['ProblemGroup', 'ProblemType', 'Problem', 'ProblemTranslation', 'TranslatedProblemQuerySet',
           'TranslatedProblemForeignKeyQuerySet', 'License']


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
        queryset = self._clone()
        alias = unique_together_left_join(queryset, ProblemTranslation, 'problem', 'language', language)
        return queryset.annotate(i18n_name=Coalesce(RawSQL('%s.name' % alias, ()), F('name'),
                                                    output_field=models.CharField()))


class TranslatedProblemForeignKeyQuerySet(QuerySet):
    def add_problem_i18n_name(self, key, language, name_field=None):
        queryset = self._clone() if name_field is None else self.annotate(_name=F(name_field))
        alias = unique_together_left_join(queryset, ProblemTranslation, 'problem', 'language', language,
                                          parent_model=Problem)
        # You must specify name_field if Problem is not yet joined into the QuerySet.
        kwargs = {key: Coalesce(RawSQL('%s.name' % alias, ()),
                                F(name_field) if name_field else RawSQLColumn(Problem, 'name'),
                                output_field=models.CharField())}
        return queryset.annotate(**kwargs)


class Problem(models.Model):
    code = models.CharField(max_length=20, verbose_name=_('problem code'), unique=True,
                            validators=[RegexValidator('^[a-z0-9]+$', _('Problem code must be ^[a-z0-9]+$'))])
    name = models.CharField(max_length=100, verbose_name=_('problem name'), db_index=True)
    description = models.TextField(verbose_name=_('problem body'))
    authors = models.ManyToManyField(Profile, verbose_name=_('creators'), blank=True, related_name='authored_problems')
    curators = models.ManyToManyField(Profile, verbose_name=_('curators'), blank=True, related_name='curated_problems',
                                      help_text=_('These users will be able to edit a problem, '
                                                  'but not be publicly shown as an author.'))
    testers = models.ManyToManyField(Profile, verbose_name=_('testers'), blank=True, related_name='tested_problems',
                                     help_text=_(
                                         'These users will be able to view a private problem, but not edit it.'))
    types = models.ManyToManyField(ProblemType, verbose_name=_('problem types'))
    group = models.ForeignKey(ProblemGroup, verbose_name=_('problem group'))
    time_limit = models.FloatField(verbose_name=_('time limit'))
    memory_limit = models.IntegerField(verbose_name=_('memory limit'))
    short_circuit = models.BooleanField(default=False)
    points = models.FloatField(verbose_name=_('points'))
    partial = models.BooleanField(verbose_name=_('allows partial points'), default=False)
    allowed_languages = models.ManyToManyField(Language, verbose_name=_('allowed languages'))
    is_public = models.BooleanField(verbose_name=_('publicly visible'), db_index=True, default=False)
    is_manually_managed = models.BooleanField(verbose_name=_('manually managed'), db_index=True, default=False,
                                              help_text=_('whether the site should be allowed to manage data or not'))
    date = models.DateTimeField(verbose_name=_('date of publishing'), null=True, blank=True, db_index=True,
                                help_text=_("Doesn't have magic ability to auto-publish due to backward compatibility"))
    banned_users = models.ManyToManyField(Profile, verbose_name=_('personae non gratae'), blank=True,
                                          help_text=_('Bans the selected users from submitting to this problem'))
    license = models.ForeignKey(License, null=True, blank=True, on_delete=models.SET_NULL)
    og_image = models.CharField(verbose_name=_('OpenGraph image'), max_length=150, blank=True)
    summary = models.TextField(blank=True, verbose_name=_('problem summary'),
                               help_text=_('Plain-text, shown in meta description tag, e.g. for social media.'))
    user_count = models.IntegerField(verbose_name=_('amount of users'), default=0,
                                     help_text=_('The amount of users on the best solutions page.'))
    ac_rate = models.FloatField(verbose_name=_('rate of AC submissions'), default=0)

    objects = TranslatedProblemQuerySet.as_manager()
    tickets = GenericRelation('Ticket')

    def __init__(self, *args, **kwargs):
        super(Problem, self).__init__(*args, **kwargs)
        self._translated_name_cache = {}
        self._i18n_name = None

    @cached_property
    def types_list(self):
        return map(user_ugettext, map(attrgetter('full_name'), self.types.all()))

    def languages_list(self):
        return self.allowed_languages.values_list('common_name', flat=True).distinct().order_by('common_name')

    def is_editor(self, profile):
        return (self.authors.filter(id=profile.id) | self.curators.filter(id=profile.id)).exists()

    def is_editable_by(self, user):
        if user.is_superuser:
            return True
        if user.has_perm('judge.edit_public_problem') and self.is_public:
            return True
        if user.has_perm('judge.change_problem'):
            return True
        if self.is_editor(user.profile):
            return True
        return False

    def is_accessible_by(self, user):
        # All users can see public problems
        if self.is_public:
            return True

        # If the user can view all problems
        if user.has_perm('judge.see_private_problem'):
            return True

        # If the user authored the problem or is a curator
        if user.has_perm('judge.edit_own_problem') and self.is_editor(user.profile):
            return True

        # If the user is in a contest containing that problem or is a tester
        if user.is_authenticated():
            return (self.testers.filter(id=user.profile.id).exists() or
                    Problem.objects.filter(id=self.id, contest__users__user=user.profile).exists())
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
    def editor_ids(self):
        return self.author_ids | self.curators.values_list('id', flat=True)

    @cached_property
    def tester_ids(self):
        return self.testers.values_list('id', flat=True)

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

    def update_stats(self):
        self.user_count = self.submission_set.filter(points__gt=0).values('user').distinct().count()
        submissions = self.submission_set.count()
        self.ac_rate = 100.0 * self.submission_set.filter(result='AC').count() / submissions if submissions else 0
        self.save()

    update_stats.alters_data = True

    def _get_limits(self, key):
        limits = {limit['language_id']: (limit['language__name'], limit[key])
                  for limit in self.language_limits.values('language_id', 'language__name', key)}
        limit_ids = set(limits.keys())
        common = []

        for cn, ids in Language.get_common_name_map().iteritems():
            if ids - limit_ids:
                continue
            limit = set(limits[id][1] for id in ids)
            if len(limit) == 1:
                limit = next(iter(limit))
                common.append((cn, limit))
                for id in ids:
                    del limits[id]

        limits = limits.values() + common
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


class ProblemTranslation(models.Model):
    problem = models.ForeignKey(Problem, verbose_name=_('problem'), related_name='translations')
    language = models.CharField(verbose_name=_('language'), max_length=7, choices=settings.LANGUAGES)
    name = models.CharField(verbose_name=_('translated name'), max_length=100, db_index=True)
    description = models.TextField(verbose_name=_('translated description'))

    class Meta:
        unique_together = ('problem', 'language')
        verbose_name = _('problem translation')
        verbose_name_plural = _('problem translations')


class LanguageLimit(models.Model):
    problem = models.ForeignKey(Problem, verbose_name=_('problem'), related_name='language_limits')
    language = models.ForeignKey(Language, verbose_name=_('language'))
    time_limit = models.FloatField(verbose_name=_('time limit'))
    memory_limit = models.IntegerField(verbose_name=_('memory limit'))

    class Meta:
        unique_together = ('problem', 'language')
        verbose_name = _('language-specific resource limit')
        verbose_name_plural = _('language-specific resource limits')
