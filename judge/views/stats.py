from hashlib import md5

from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils.translation import ugettext as _

from judge.models import Language


def language(request):
    language_count = Language.objects.annotate(count=Count('submission'))
    languages = list(language_count.filter(count__gte=1000).values('key', 'name', 'short_name', 'count')
                                   .order_by('-count'))
    for language in languages:
        hash = md5(language['key']).hexdigest()[:6]
        r, g, b = int(hash[:2], 16), int(hash[2:4], 16), int(hash[4:6], 16),
        language['color'] = '#%02X%02X%02X' % (r, g, b)
        language['highlight'] = '#%02X%02X%02X' % (min(int(r * 1.2), 255),
                                                   min(int(g * 1.2), 255),
                                                   min(int(b * 1.2), 255))
    return render(request, 'stats/language.jade', {
        'title': _('Language statistics'), 'tab': 'language',
        'languages': languages,
        'other': language_count.filter(count__lt=1000).aggregate(total=Sum('count'))['total']
    })
