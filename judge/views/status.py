from collections import defaultdict
from functools import partial

from django.shortcuts import render
from django.utils import six
from django.utils.translation import gettext as _
from packaging import version

from judge.models import Judge, Language, RuntimeVersion

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
        'runtime_version_data': Judge.runtime_versions(),
        'see_all_judges': see_all,
    })


def status_table(request):
    see_all, judges = get_judges(request)
    return render(request, 'status/judge-status-table.html', {
        'judges': judges,
        'runtime_version_data': Judge.runtime_versions(),
        'see_all_judges': see_all,
    })


class LatestList(list):
    __slots__ = ('versions', 'is_latest')


def compare_version_list(x, y):
    if sorted(x.keys()) != sorted(y.keys()):
        return False
    for k in x.keys():
        if len(x[k]) != len(y[k]):
            return False
        for a, b in zip(x[k], y[k]):
            if a.name != b.name:
                return False
            if a.version != b.version:
                return False
    return True


def version_matrix(request):
    matrix = defaultdict(partial(defaultdict, LatestList))
    latest = defaultdict(list)
    groups = defaultdict(list)

    judges = {judge.id: judge.name for judge in Judge.objects.filter(online=True)}
    languages = Language.objects.filter(judges__online=True).distinct()

    for runtime in RuntimeVersion.objects.filter(judge__online=True).order_by('priority'):
        matrix[runtime.judge_id][runtime.language_id].append(runtime)

    for judge, data in six.iteritems(matrix):
        name_tuple = judges[judge].rpartition('.')
        groups[name_tuple[0] or name_tuple[-1]].append((judges[judge], data))

    matrix = {}
    for group, data in six.iteritems(groups):
        if len(data) == 1:
            judge, data = data[0]
            matrix[judge] = data
            continue

        ds = list(range(len(data)))
        size = [1] * len(data)
        for i, (p, x) in enumerate(data):
            if ds[i] != i:
                continue
            for j, (q, y) in enumerate(data):
                if i != j and compare_version_list(x, y):
                    ds[j] = i
                    size[i] += 1
                    size[j] = 0

        rep = max(range(len(data)), key=size.__getitem__)
        matrix[group] = data[rep][1]
        for i, (j, x) in enumerate(data):
            if ds[i] != rep:
                matrix[j] = x

    for data in six.itervalues(matrix):
        for language, versions in six.iteritems(data):
            versions.versions = [version.parse(runtime.version) for runtime in versions]
            if versions.versions > latest[language]:
                latest[language] = versions.versions

    for data in six.itervalues(matrix):
        for language, versions in six.iteritems(data):
            versions.is_latest = versions.versions == latest[language]

    languages = sorted(languages, key=lambda lang: version.parse(lang.name))
    return render(request, 'status/versions.html', {
        'title': _('Version matrix'),
        'judges': sorted(matrix.keys()),
        'languages': languages,
        'matrix': matrix,
    })
