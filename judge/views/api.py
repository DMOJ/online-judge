from operator import attrgetter

from django.db.models import Prefetch, F
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404

from dmoj import settings
from judge.models import Contest, Problem, Profile, Submission, ContestTag


def sane_time_repr(delta):
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    return '%02d:%02d:%02d' % (days, hours, minutes)


def api_contest_list(request):
    contests = {}
    for c in Contest.objects.filter(is_public=True, is_private=False).prefetch_related(
            Prefetch('tags', queryset=ContestTag.objects.only('name'), to_attr='tag_list')).defer('description'):
        contests[c.key] = {
            'name': c.name,
            'start_time': c.start_time.isoformat(),
            'end_time': c.end_time.isoformat(),
            'time_limit': c.time_limit and sane_time_repr(c.time_limit),
            'labels': map(attrgetter('name'), c.tag_list),
        }
    return JsonResponse(contests)


def api_problem_list(request):
    qs = Problem.objects.filter(is_public=True)
    if settings.ENABLE_FTS and 'search' in request.GET:
        query = ' '.join(request.GET.getlist('search')).strip()
        if query:
            qs = qs.search(query)

    problems = {}
    for code, points, partial, name, group in qs.values_list('code', 'points', 'partial', 'name', 'group__full_name'):
        problems[code] = {
            'points': points,
            'partial': partial,
            'name': name,
            'group': group
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
    for username, name, points, rank in Profile.objects.values_list('user__username', 'name', 'points', 'display_rank'):
        users[username] = {
            'display_name': name,
            'points': points,
            'rank': rank
        }
    return JsonResponse(users)


def api_user_info(request, user):
    p = get_object_or_404(Profile, user__username=user)
    submissions = list(Submission.objects.filter(case_points=F('case_total'), user=p, problem__is_public=True)
                       .values('problem').distinct().values_list('problem__code', flat=True))
    return JsonResponse({
        'display_name': p.name,
        'points': p.points,
        'rank': p.display_rank,
        'solved_problems': submissions,
    })


def api_user_submissions(request, user):
    p = get_object_or_404(Profile, user__username=user)

    subs = Submission.objects.filter(user=p, problem__is_public=True)
    data = {}

    for s in subs.values('id', 'problem__code', 'time', 'memory', 'points', 'language__key', 'status', 'result'):
        data[s['id']] = {
            'problem': s['problem__code'],
            'time': s['time'],
            'memory': s['memory'],
            'points': s['points'],
            'language': s['language__key'],
            'status': s['status'],
            'result': s['result'],
        }
    return JsonResponse(data)
