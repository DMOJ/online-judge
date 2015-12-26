from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils.translation import ugettext as _

from judge.models import Language


def language(request):
    language_count = Language.objects.annotate(count=Count('submission_set'))
    return render(request, 'stats/language.jade', {
        'title': _('Language statistics'), 'tab': 'language',
        'languages': language_count.filter(count__gte=1000).values('key', 'name', 'short_name', 'count'),
        'other': language_count.filter(count__lt=1000).aggregate(total=Sum('count'))['total']
    })
