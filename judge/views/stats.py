from hashlib import md5

from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import ugettext as _

from judge.models import Language


def language_data(request):
    language_count = Language.objects.annotate(count=Count('submission'))
    languages = language_count.filter(count__gte=1000).values('key', 'name', 'short_name', 'count').order_by('-count')
    data = []
    for language in languages:
        hash = md5(language['key']).hexdigest()[:6]
        r, g, b = int(hash[:2], 16), int(hash[2:4], 16), int(hash[4:6], 16),
        data.append({
            'value': languages['count'], 'label': languages['name'],
            'color': '#%02X%02X%02X' % (r, g, b),
            'highlight': '#%02X%02X%02X' % (min(int(r * 1.2), 255),
                                            min(int(g * 1.2), 255),
                                            min(int(b * 1.2), 255))
        })
    data.append({
        'value': language_count.filter(count__lt=1000).aggregate(total=Sum('count'))['total'],
        'label': 'Other', 'color': '#FDB45C', 'highlight': '#FFC870',
    })
    return JsonResponse(data)


def language(request):
    return render(request, 'stats/language.jade', {
        'title': _('Language statistics'), 'tab': 'language'
    })
