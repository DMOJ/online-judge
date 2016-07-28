from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404

from judge.models import Contest, Problem, Profile, Submission


def sane_time_repr(delta):
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    return '%02d:%02d:%02d' % (days, hours, minutes)


def api_contest_list(request):
    contests = {}
    for c in Contest.objects.filter(is_public=True, is_private=False):
        contests[c.key] = {
            'name': c.name,
            'start_time': c.start_time.isoformat(),
            'end_time':  c.end_time.isoformat(),
            'time_limit': c.time_limit and sane_time_repr(c.time_limit),
            'labels': ['external'] if c.is_external else [],
        }
    return JsonResponse(contests)


def api_problem_list(request):
    problems = {}
    for p in Problem.objects.filter(is_public=True):
        problems[p.code] = {
            'points': p.points,
            'partial': p.partial,
            'name': p.name,
            'group': p.group.full_name
        }
    return JsonResponse(problems)


def api_problem_info(request, problem):
    p = get_object_or_404(Problem, code=problem)
    if not p.is_accessible_by(request.user):
        raise Http404()
    return JsonResponse({
        'name': p.name,
        'authors': list(p.authors.values_list('user__username', flat=True)),
        'types': list(p.types.values_list('full_name', flat=True)),
        'group': p.group.full_name,
        'time_limit': p.time_limit,
        'memory_limit': p.memory_limit,
        'points': p.points,
        'partial': p.partial,
        'languages': list(p.allowed_languages.values_list('key', flat=True)),
    })


def api_user_list(request):
    users = {}
    for p in Profile.objects.select_related('user').only('user__username', 'name', 'points', 'display_rank'):
        users[p.user.username] = {
            'display_name': p.name,
            'points': p.points,
            'rank': p.display_rank
        }
    return JsonResponse(users)


def api_user_info(request, user):
    p = get_object_or_404(Profile, user__username=user)
    return JsonResponse({
        'display_name': p.name,
        'points': p.points,
        'rank': p.display_rank,
        'solved_problems': [],  # TODO
    })


def api_user_submissions(request, user):
    p = get_object_or_404(Profile, user__username=user)

    subs = Submission.objects.filter(user=p, problem__is_public=True).select_related('problem', 'language') \
        .only('id', 'problem__code', 'time', 'memory', 'points', 'language__key', 'status', 'result')
    data = {}

    for s in subs:
        data[s.id] = {
            'problem': s.problem.code,
            'time': s.time,
            'memory': s.memory,
            'points': s.points,
            'language': s.language.key,
            'status': s.status,
            'result': s.result
        }
    return JsonResponse(data)
