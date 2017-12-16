from collections import defaultdict
from distutils.version import LooseVersion

from django.shortcuts import render
from django.utils import six
from django.utils.translation import ugettext as _

from judge.models import Judge, RuntimeVersion, Language

__all__ = ['status_all', 'status_table']


def get_judges(request):
    if request.user.is_superuser or request.user.is_staff:
        return True, Judge.objects.order_by('-online', 'name')
    else:
        return False, Judge.objects.filter(online=True)


def status_all(request):
    see_all, judges = get_judges(request)
    return render(request, 'status/judge-status.html', {
        'title': _('Status'),
        'judges': judges,
        'see_all_judges': see_all,
    })


def status_table(request):
    see_all, judges = get_judges(request)
    return render(request, 'status/judge-status-table.html', {
        'judges': judges,
        'see_all_judges': see_all,
    })


class LatestList(list):
    __slots__ = ('versions', 'is_latest')


def version_matrix(request):
    matrix = defaultdict(LatestList)
    latest = defaultdict(list)

    judges = Judge.objects.filter(online=True).order_by('name')
    languages = Language.objects.filter(judges__isnull=False)

    for version in RuntimeVersion.objects.filter(judge__online=True).order_by('priority'):
        matrix[version.judge_id, version.language_id].append(version)

    for (judge, language), versions in six.iteritems(matrix):
        versions.versions = [LooseVersion(runtime.version) for runtime in versions]
        if versions.versions > latest[language]:
            latest[language] = versions.versions

    for (judge, language), versions in six.iteritems(matrix):
        versions.is_latest = versions.versions == latest[language]

    return render(request, 'status/versions.html', {
        'title': _('Version matrix'),
        'judges': judges,
        'languages': languages,
        'matrix': matrix,
    })
