from django.shortcuts import render
from django.utils.translation import ugettext as _

from judge.models import Judge

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


