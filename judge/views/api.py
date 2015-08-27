from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import *

import json
from judge.models import Contest, Problem, Profile, Submission


def sane_time_repr(delta):
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    return '%02d:%02d:%02d' % (days, hours, minutes)


def api_contest_list(request):
    js = {}
    for c in Contest.objects.filter(is_public=True, is_private=False):
        js[c.key] = {
            'name': c.name,
            'start_time': c.start_time.isoformat(),
            'end_time':  c.end_time.isoformat(),
            'time_limit': c.time_limit and sane_time_repr(c.time_limit),
        }
    return HttpResponse(json.dumps(js), content_type='application/json')


def api_problem_list(request):
    js = {}
    for p in Problem.objects.filter(is_public=True):
        js[p.code] = {
            'points': p.points,
            'partial': p.partial,
            'name': p.name,
            'group': p.group.full_name
        }
    return HttpResponse(json.dumps(js), content_type='application/json')


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
    return HttpResponse(json.dumps(js), content_type='application/json')


def api_user_list(request):
    js = {}
    for p in Profile.objects.select_related('user'):
        js[p.user.username] = {
            'display_name': p.name,
            'points': p.points,
            'rank': p.display_rank
        }
    return HttpResponse(json.dumps(js), content_type='application/json')


def api_user_info(request, user):
    try:
        p = Profile.objects.get(user__username=user)
        js = {
            'display_name': p.name,
            'points': p.points,
            'rank': p.display_rank,
            'solved_problems': [],  # TODO
        }
    except ObjectDoesNotExist:
        raise Http404()
    return HttpResponse(json.dumps(js), content_type='application/json')


def api_user_submissions(request, user):
    try:
        p = Profile.objects.get(user__username=user)
        subs = Submission.objects.filter(user=p, problem__is_public=True).select_related('problem', 'language') \
            .only('id', 'problem__code', 'time', 'memory', 'points', 'language__key', 'status', 'result')
        js = {}

        for s in subs:
            js[s.id] = {
                'problem': s.problem.code,
                'time': s.time,
                'memory': s.memory,
                'points': s.points,
                'language': s.language.key,
                'status': s.status,
                'result': s.result
            }
    except ObjectDoesNotExist:
        raise Http404()
    return HttpResponse(json.dumps(js), content_type='application/json')