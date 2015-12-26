from zlib import adler32

from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils.translation import ugettext as _

from judge.models import Language


def language(request):
    language_count = Language.objects.annotate(count=Count('submission'))
    languages = list(language_count.filter(count__gte=1000).values('key', 'name', 'short_name', 'count')
                                   .order_by('-count'))
    for language in languages:
        color = adler32(language['key']) & 0xFFFFFF
        language['color'] = '#%06X' % color
        language['highlight'] = '#%06X' % (~color & 0xFFFFFF)
    return render(request, 'stats/language.jade', {
        'title': _('Language statistics'), 'tab': 'language',
        'languages': languages,
        'other': language_count.filter(count__lt=1000).aggregate(total=Sum('count'))['total']
    })
