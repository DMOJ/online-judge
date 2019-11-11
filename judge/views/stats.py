from itertools import chain, repeat
from operator import itemgetter

from django.conf import settings
from django.db.models import Case, Count, FloatField, IntegerField, Value, When
from django.db.models.expressions import CombinedExpression
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from judge.models import Language, Submission
from judge.utils.chart import chart_colors, highlight_colors


ac_count = Count(Case(When(submission__result='AC', then=Value(1)), output_field=IntegerField()))


def repeat_chain(iterable):
    return chain.from_iterable(repeat(iterable))


def language_data(request, language_count=Language.objects.annotate(count=Count('submission'))):
    languages = language_count.filter(count__gt=0).values('key', 'name', 'count').order_by('-count')
    num_languages = min(len(languages), settings.DMOJ_STATS_LANGUAGE_THRESHOLD)
    other_count = sum(map(itemgetter('count'), languages[num_languages:]))

    return JsonResponse({
        'labels': list(map(itemgetter('name'), languages[:num_languages])) + ['Other'],
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
