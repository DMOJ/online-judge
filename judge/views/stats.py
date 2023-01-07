from operator import itemgetter

from django.conf import settings
from django.db.models import Count, FloatField, Q, Value
from django.db.models.expressions import CombinedExpression
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from judge.models import Language, Submission
from judge.utils.stats import chart_colors, get_bar_chart, get_pie_chart, highlight_colors


ac_count = Count(Value(1), filter=Q(submission__result='AC'))


def language_data(request, language_count=Language.objects.annotate(count=Count('submission'))):
    languages = language_count.filter(count__gt=0).values('name', 'count').order_by('-count')
    num_languages = min(len(languages), settings.DMOJ_STATS_LANGUAGE_THRESHOLD)
    other_count = sum(map(itemgetter('count'), languages[num_languages:]))

    return JsonResponse({
        'labels': list(map(itemgetter('name'), languages[:num_languages])) + [_('Other')],
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
        data.append((str(Submission.USER_DISPLAY_CODES[res]), count))

    return JsonResponse(get_pie_chart(data), safe=False)


def ac_rate(request):
    rate = CombinedExpression(ac_count / Count('submission'), '*', Value(100.0), output_field=FloatField())
    data = Language.objects.annotate(total=Count('submission'), ac_rate=rate).filter(total__gt=0) \
        .order_by('total').values_list('name', 'ac_rate')
    return JsonResponse(get_bar_chart(list(data)))


def language(request):
    return render(request, 'stats/language.html', {
        'title': _('Language statistics'), 'tab': 'language',
    })
