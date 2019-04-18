from collections import OrderedDict, defaultdict
from operator import attrgetter

from django.core.cache import cache
from django.db.models import CASCADE
from django.urls import reverse
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from judge.judgeapi import disconnect_judge

__all__ = ['Language', 'RuntimeVersion', 'Judge']


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
    template = models.TextField(verbose_name=_('code template'),
                                help_text=_('Code template to display in submission editor.'), blank=True)
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
        for id, version_list in runtimes.items():
            lang_versions.append((id, sorted(version_list, key=lambda a: tuple(map(int, a.split('.'))))))
        return lang_versions

    @classmethod
    def get_common_name_map(cls):
        result = cache.get('lang:cn_map')
        if result is not None:
            return result
        result = defaultdict(set)
        for id, cn in Language.objects.values_list('id', 'common_name'):
            result[cn].add(id)
        result = {id: cns for id, cns in result.items() if len(cns) > 1}
        cache.set('lang:cn_map', result, 86400)
        return result

    @cached_property
    def short_display_name(self):
        return self.short_name or self.key

    def __str__(self):
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
        return Language.objects.get_or_create(key='PY2', defaults={'name': 'Python 2'})[0]

    def get_absolute_url(self):
        return reverse('runtime_list') + '#' + self.key

    class Meta:
        ordering = ['key']
        verbose_name = _('language')
        verbose_name_plural = _('languages')


class RuntimeVersion(models.Model):
    language = models.ForeignKey(Language, verbose_name=_('language to which this runtime belongs'), on_delete=CASCADE)
    judge = models.ForeignKey('Judge', verbose_name=_('judge on which this runtime exists'), on_delete=CASCADE)
    name = models.CharField(max_length=64, verbose_name=_('runtime name'))
    version = models.CharField(max_length=64, verbose_name=_('runtime version'), blank=True)
    priority = models.IntegerField(verbose_name=_('order in which to display this runtime'), default=0)


class Judge(models.Model):
    name = models.CharField(max_length=50, help_text=_('Server name, hostname-style'), unique=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('time of creation'))
    auth_key = models.CharField(max_length=100, help_text=_('A key to authenticated this judge'),
                                verbose_name=_('authentication key'))
    is_blocked = models.BooleanField(verbose_name=_('block judge'), default=False,
                                     help_text=_('Whether this judge should be blocked from connecting, '
                                                 'even if its key is correct.'))
    online = models.BooleanField(verbose_name=_('judge online status'), default=False)
    start_time = models.DateTimeField(verbose_name=_('judge start time'), null=True)
    ping = models.FloatField(verbose_name=_('response time'), null=True)
    load = models.FloatField(verbose_name=_('system load'), null=True,
                             help_text=_('Load for the last minute, divided by processors to be fair.'))
    description = models.TextField(blank=True, verbose_name=_('description'))
    last_ip = models.GenericIPAddressField(verbose_name='Last connected IP', blank=True, null=True)
    problems = models.ManyToManyField('Problem', verbose_name=_('problems'), related_name='judges')
    runtimes = models.ManyToManyField(Language, verbose_name=_('judges'), related_name='judges')

    def __str__(self):
        return self.name

    def disconnect(self, force=False):
        disconnect_judge(self, force=force)

    disconnect.alters_data = True

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

        return list(ret.items())

    @cached_property
    def uptime(self):
        return timezone.now() - self.start_time if self.online else 'N/A'

    @cached_property
    def ping_ms(self):
        return self.ping * 1000 if self.ping is not None else None

    @cached_property
    def runtime_list(self):
        return map(attrgetter('name'), self.runtimes.all())

    class Meta:
        ordering = ['name']
        verbose_name = _('judge')
        verbose_name_plural = _('judges')
