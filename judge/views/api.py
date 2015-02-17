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
        js[p.code] = {
            'points': p.points,
            'partial': p.partial,
            'name': p.name,
            'group': p.group.full_name
        }
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')


def api_problem_info(request, problem):
    js = {}
    try:
        p = Problem.objects.get(code=problem)
        js = {
            'name': p.name,
            'authors': [a.name for a in p.authors.all()],
            'types': [t.full_name for t in p.types.all()],
            'group': p.group.full_name,
            'time_limit': p.time_limit,
            'memory_limit': p.memory_limit,
            'points': p.points,
            'partial': p.partial,
            'languages': [l.key for l in p.allowed_languages.all()],
        }
    except ObjectDoesNotExist:
        pass
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')