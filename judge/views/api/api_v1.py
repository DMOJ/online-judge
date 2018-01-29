from operator import attrgetter

from django.db.models import Prefetch, F
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404

from dmoj import settings
from judge.models import Contest, Problem, Profile, Submission, ContestTag
from judge.views.contests import base_contest_ranking_list


def sane_time_repr(delta):
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    return '%02d:%02d:%02d' % (days, hours, minutes)


def api_v1_contest_list(request):
    queryset = Contest.objects.filter(is_public=True, is_private=False).prefetch_related(
        Prefetch('tags', queryset=ContestTag.objects.only('name'), to_attr='tag_list')).defer('description')

    return JsonResponse({c.key: {
        'name': c.name,
        'start_time': c.start_time.isoformat(),
        'end_time': c.end_time.isoformat(),
        'time_limit': c.time_limit and sane_time_repr(c.time_limit),
        'labels': map(attrgetter('name'), c.tag_list),
    } for c in queryset})


def api_v1_contest_detail(request, contest):
    contest = get_object_or_404(Contest, key=contest)
    if not contest.can_see_scoreboard(request):
        raise Http404()

    problems = list(contest.contest_problems.select_related('problem')
                    .defer('problem__description').order_by('order'))
    users = base_contest_ranking_list(contest, problems, contest.users.filter(virtual=0)
                                      .prefetch_related('user__organizations')
                                      .order_by('-score', 'cumtime'))
    return JsonResponse({
        'time_limit': contest.time_limit and contest.time_limit.total_seconds(),
        'start_time': contest.start_time.isoformat(),
        'end_time': contest.end_time.isoformat(),
        'tags': list(contest.tags.values_list('name', flat=True)),
        'problems': [
            {
                'points': int(problem.points),
                'partial': problem.partial,
                'name': problem.problem.name,
                'code': problem.problem.code,
            } for problem in problems],
        'rankings': [
            {
                'user': user.user.username,
                'points': user.points,
                'cumtime': user.cumtime,
                'solutions': [{
                                  'points': int(sol.points),
                                  'time': sol.time.total_seconds()
                              } if sol else None for sol in user.problems]
            } for user in users]
    })


def api_v1_problem_list(request):
    queryset = Problem.objects.filter(is_public=True)
    if settings.ENABLE_FTS and 'search' in request.GET:
        query = ' '.join(request.GET.getlist('search')).strip()
        if query:
            queryset = queryset.search(query)
    queryset = queryset.values_list('code', 'points', 'partial', 'name', 'group__full_name')

    return JsonResponse({code: {
        'points': points,
        'partial': partial,
        'name': name,
        'group': group
    } for code, points, partial, name, group in queryset})


def api_v1_problem_info(request, problem):
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


def api_v1_user_list(request):
    queryset = Profile.objects.values_list('user__username', 'name', 'points', 'display_rank')
    return JsonResponse({username: {
        'display_name': name,
        'points': points,
        'rank': rank
    } for username, name, points, rank in queryset})


def api_v1_user_info(request, user):
    profile = get_object_or_404(Profile, user__username=user)
    submissions = list(Submission.objects.filter(case_points=F('case_total'), user=profile, problem__is_public=True)
                       .values('problem').distinct().values_list('problem__code', flat=True))
    return JsonResponse({
        'display_name': profile.name,
        'points': profile.points,
        'rank': profile.display_rank,
        'solved_problems': submissions,
        'organizations': list(profile.organizations.values_list('key', flat=True)),
    })


def api_v1_user_submissions(request, user):
    profile = get_object_or_404(Profile, user__username=user)
    subs = Submission.objects.filter(user=profile, problem__is_public=True)

    return JsonResponse({sub['id']: {
        'problem': sub['problem__code'],
        'time': sub['time'],
        'memory': sub['memory'],
        'points': sub['points'],
        'language': sub['language__key'],
        'status': sub['status'],
        'result': sub['result'],
    } for sub in subs.values('id', 'problem__code', 'time', 'memory', 'points', 'language__key', 'status', 'result')})
