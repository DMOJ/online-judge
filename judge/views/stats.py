from itertools import repeat, chain

from django.db.models import Count, Sum, Case, When, IntegerField, Value
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import ugettext as _

from judge.models import Language

chart_colors = [0x3366CC, 0xDC3912, 0xFF9900, 0x109618, 0x990099, 0x3B3EAC, 0x0099C6, 0xDD4477, 0x66AA00, 0xB82E2E,
                0x316395, 0x994499, 0x22AA99, 0xAAAA11, 0x6633CC, 0xE67300, 0x8B0707, 0x329262, 0x5574A6, 0x3B3EAC]
highlight_colors = []


def _highlight_colors():
    for color in chart_colors:
        r, g, b = color >> 16, (color >> 8) & 0xFF, color & 0xFF
        highlight_colors.append('#%02X%02X%02X' % (min(int(r * 1.2), 255),
                                                   min(int(g * 1.2), 255),
                                                   min(int(b * 1.2), 255)))

_highlight_colors()
del _highlight_colors

chart_colors = map('#%06X'.__mod__, chart_colors)


def repeat_chain(iterable):
    return chain.from_iterable(repeat(iterable))


def language_data(request, language_count=Language.objects.annotate(count=Count('submission'))):
    languages = language_count.filter(count__gte=1000).values('key', 'name', 'short_name', 'count').order_by('-count')
    data = []
    for language, color, highlight in zip(languages, chart_colors, highlight_colors):
        data.append({
            'value': language['count'], 'label': language['name'],
            'color': color, 'highlight': highlight,
        })
    data.append({
        'value': language_count.filter(count__lt=1000).aggregate(total=Sum('count'))['total'],
        'label': 'Other', 'color': '#FDB45C', 'highlight': '#FFC870',
    })
    return JsonResponse(data, safe=False)


def ac_language_data(request):
    return language_data(request, Language.objects.annotate(count=Count(Case(
        When(submission__result='AC', then=Value(1)), output_field=IntegerField()
    ))))


def language(request):
    return render(request, 'stats/language.jade', {
        'title': _('Language statistics'), 'tab': 'language'
    })
