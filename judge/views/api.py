from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import *

import json
from judge.models import Contest, Problem
from judge.templatetags.timedelta import nice_repr


def api_contest_list(request):
    js = {}
    for c in Contest.objects.filter(is_public=True):
        js[c.key] = {
            'name': c.name,
            'free_start': c.free_start,
            'start_time': c.start_time.isoformat() if c.start_time is not None else None,
            'time_limit': nice_repr(c.time_limit, 'concise'),
            'ongoing': c.ongoing
        }
    return HttpResponse(json.dumps(js), mimetype='application/json')


def api_problem_list(request):
    js = {}
    for p in Problem.objects.filter(is_public=True):
        js[p.code] = {
            'points': p.points,
            'partial': p.partial,
            'name': p.name,
            'group': p.group.full_name
        }
    return HttpResponse(json.dumps(js), mimetype='application/json')


def api_problem_info(request, problem):
    try:
        p = Problem.objects.get(code=problem)
        js = {
            'name': p.name,
            'authors': list(p.authors.values_list('user__username', flat=True)),
            'types': list(p.types.values_list('full_name', flat=True)),
            'group': p.group.full_name,
            'time_limit': p.time_limit,
            'memory_limit': p.memory_limit,
            'points': p.points,
            'partial': p.partial,
            'languages': list(p.allowed_languages.values_list('key', flat=True)),
        }
    except ObjectDoesNotExist:
        raise Http404()
    return HttpResponse(json.dumps(js), mimetype='application/json')