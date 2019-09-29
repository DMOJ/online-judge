from itertools import chain, repeat
from operator import itemgetter

from django.conf import settings
from django.db.models import Case, Count, FloatField, IntegerField, Value, When
from django.db.models.expressions import CombinedExpression
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from judge.models import Language, Submission

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

chart_colors = list(map('#%06X'.__mod__, chart_colors))
ac_count = Count(Case(When(submission__result='AC', then=Value(1)), output_field=IntegerField()))


def repeat_chain(iterable):
    return chain.from_iterable(repeat(iterable))


def language_data(request, language_count=Language.objects.annotate(count=Count('submission'))):
    languages = language_count.filter(count__gt=0).values('key', 'name', 'count').order_by('-count')
    threshold = getattr(settings, 'DMOJ_STATS_LANGUAGE_THRESHOLD', 10)
    num_languages = min(len(languages), threshold)
    other_count = sum(map(itemgetter('count'), languages[num_languages:]))

    return JsonResponse({
        'labels': list(map(itemgetter('name'), languages)) + ['Other'],
        'datasets': [
            {
                'backgroundColor': chart_colors[:num_languages] + ['#FDB45C'],
                'highlightBackgroundColor': highlight_colors[:num_languages] + ['#FFC870'],
                'data': list(map(itemgetter('count'), languages[:num_languages])) + [other_count],
            },
        ],
    }, safe=False)


def ac_language_data(request):
    return language_data(request, Language.objects.annotate(count=ac_count))


def status_data(request, statuses=None):
    if not statuses:
        statuses = (Submission.objects.values('result').annotate(count=Count('result'))
                    .values('result', 'count').order_by('-count'))
    data = []
    for status in statuses:
        res = status['result']
        if not res:
            continue
        count = status['count']
        data.append({
            'count': count, 'result': str(Submission.USER_DISPLAY_CODES[res]),
        })

    return JsonResponse({
        'labels': list(map(itemgetter('result'), data)),
        'datasets': [
            {
                'backgroundColor': chart_colors,
                'highlightBackgroundColor': highlight_colors,
                'data': list(map(itemgetter('count'), data)),
            },
        ],
    }, safe=False)


def ac_rate(request):
    rate = CombinedExpression(ac_count / Count('submission'), '*', Value(100.0), output_field=FloatField())
    data = Language.objects.annotate(total=Count('submission'), ac_rate=rate).filter(total__gt=0) \
        .values('key', 'name', 'ac_rate').order_by('total')
    return JsonResponse({
        'labels': list(map(itemgetter('name'), data)),
        'datasets': [
            {
                'backgroundColor': 'rgba(151,187,205,0.5)',
                'borderColor': 'rgba(151,187,205,0.8)',
                'borderWidth': 1,
                'hoverBackgroundColor': 'rgba(151,187,205,0.75)',
                'hoverBorderColor': 'rgba(151,187,205,1)',
                'data': list(map(itemgetter('ac_rate'), data)),
            },
        ],
    })


def language(request):
    return render(request, 'stats/language.html', {
        'title': _('Language statistics'), 'tab': 'language',
    })
