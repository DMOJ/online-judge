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
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')


def api_problem_list(request):
    js = {}
    for p in Problem.objects.filter(is_public=True):
        js[p.key] = {
            'points': p.points,
            'partial': p.partial,
            'name': p.name,
            'group': p.group
        }
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')


def api_problem_info(request, problem):
    js = {}
    try:
        p = Problem.objects.get(key=problem)
        js = {
            'name': p.name,
            'authors': p.authors,
            'types': p.types,
            'group': p.group,
            'time_limit': p.time_limit,
            'memory_limit': p.memory_limit,
            'points': p.points,
            'partial': p.partial,
            'languages': p.allowed_languages,
        }
    except ObjectDoesNotExist:
        pass
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')