from operator import attrgetter

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models import Prefetch, F
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404

from dmoj import settings
from judge.models import Contest, ContestParticipation, ContestTag, Problem, Profile, Submission
from judge.views.contests import base_contest_ranking_list


def error(message):
    return JsonResponse({
        "error": message
    }, status=422)


def sane_time_repr(delta):
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    return '%02d:%02d:%02d' % (days, hours, minutes)

def get_request_user(request):
    try:
        username = request.GET['id']
        token = request.GET['token']
        user = User.objects.get(username=username)
        if user.profile.api_token != token:
            raise ObjectDoesNotExist()
    except (KeyError, ObjectDoesNotExist):
        return request.user
    else:
        return user 

def api_v1_contest_list(request):
    user = get_request_user(request)

    if user.profile.is_contest_account:
        return JsonReponse({})

    queryset = Contest.contests_list(user).prefetch_related(
        Prefetch('tags', queryset=ContestTag.objects.only('name'), to_attr='tag_list')).defer('description')
    
    return JsonResponse({c.key: {
        'name': c.name,
        'start_time': c.start_time.isoformat(),
        'end_time': c.end_time.isoformat(),
        'time_limit': c.time_limit and sane_time_repr(c.time_limit),
        'labels': map(attrgetter('name'), c.tag_list),
    } for c in queryset})


def api_v1_contest_detail(request, contest):
    user = get_request_user(request)

    contest = get_object_or_404(Contest, key=contest)

    if not contest.is_accessible_by(user) or user.profile.is_contest_account:
        raise Http404()

    in_contest = contest.is_in_contest(user)
    can_see_rankings = contest.can_see_scoreboard(user)
    if contest.hide_scoreboard and in_contest:
        can_see_rankings = False

    problems = list(contest.contest_problems.select_related('problem')
                    .defer('problem__description').order_by('order'))
    users = base_contest_ranking_list(contest, problems, contest.users.filter(virtual=0, user__is_unlisted=False)
                                      .prefetch_related('user__organizations')
                                      .order_by('-score', 'cumtime')) if can_see_rankings else []
    if not (in_contest or contest.ended or request.user.is_superuser \
            or contest.organizers.filter(id=request.user.profile.id).exists()):
        problems = []

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
    user = get_request_user(request)

    if not user.is_authenticated or user.profile.is_contest_account:
        return JsonResponse({})

    queryset = Problem.problems_list(user)
    
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
    user = get_request_user(request)

    if not user.is_authenticated or user.profile.is_contest_account:
        raise Http404()

    p = get_object_or_404(Problem, code=problem)
    if not p.is_accessible_by(user):
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
    user = get_request_user(request)

    if not user.is_authenticated or user.profile.is_contest_account:
        return JsonResponse({})

    queryset = Profile.objects.filter(is_unlisted=False).values_list('user__username', 'points', 'display_rank')
    return JsonResponse({username: {
        'points': points,
        'rank': rank
    } for username, points, rank in queryset})


def api_v1_user_info(request, username):
    user = get_request_user(request)

    if not user.is_authenticated or user.profile.is_contest_account:
        return JsonResponse({})

    profile = get_object_or_404(Profile, user__username=username)
    submissions = list(Submission.objects.filter(case_points=F('case_total'), user=profile, problem__is_public=True, problem__is_organization_private=False)
                       .values('problem').distinct().values_list('problem__code', flat=True))
    resp = {
        'points': profile.points,
        'rank': profile.display_rank,
        'solved_problems': submissions,
        'organizations': list(profile.organizations.values_list('id', flat=True)),
    }

    if user.has_perm('judge.view_name'):
        resp['name'] = profile.user.get_full_name()
    
    last_rating = profile.ratings.last()

    contest_history = {}
    if not profile.is_unlisted:
        for contest_key, rating, volatility in ContestParticipation.objects.filter(user=profile, virtual=0, contest__is_public=True, contest__is_private=False) \
                                                                   .values_list('contest__key', 'rating__rating', 'rating__volatility'):
            contest_history[contest_key] = {
                'rating': rating,
                'volatility': volatility,
            }

    resp['contests'] = {
        'current_rating': last_rating.rating if last_rating else None,
        'volatility': last_rating.volatility if last_rating else None,
        'history': contest_history,
    }

    return JsonResponse(resp)


def api_v1_user_submissions(request, username):
    user = get_request_user(request)

    if not user.is_authenticated or user.profile.is_contest_account:
        return JsonResponse({})

    profile = get_object_or_404(Profile, user__username=username)
    subs = Submission.objects.filter(user=profile, problem__is_public=True, problem__is_organization_private=False)

    return JsonResponse({sub['id']: {
        'problem': sub['problem__code'],
        'time': sub['time'],
        'memory': sub['memory'],
        'points': sub['points'],
        'language': sub['language__key'],
        'status': sub['status'],
        'result': sub['result'],
    } for sub in subs.values('id', 'problem__code', 'time', 'memory', 'points', 'language__key', 'status', 'result')})


def api_v1_submission_list(request):
    pass


def api_v1_submission_detail(request, submission):
    user = get_request_user(request)

    submission = get_object_or_404(Submission, id=submission)
    
    if not submission.is_accessible_by(user) or user.profile.is_contest_account:
        raise Http404()

    if user.profile.current_contest is not None:
        return JsonResponse({})

    resp = {
        'problem': submission.problem.code,
        'user': submission.user.user.username,
        'time': submission.time,
        'memory': submission.memory,
        'points': submission.points,
        'total': submission.problem.points,
        'language': submission.language.key,
        'status': submission.status,
        'result': submission.result,
        'cases': [{
            'case_number': case['case'],
            'status': case['status'],
            'time': case['time'],
            'memory': case['memory'],
            'points': case['points'],
            'total': case['total'],
            'clipped_output': case['output'],
        } for case in submission.test_cases.all().values('case', 'status', 'time', 'memory', 'points', 'total', 'output')]
    }
    
    return JsonResponse(resp)

def api_v1_submission_source(request, submission):
    user = get_request_user(request)

    submission = get_object_or_404(Submission, id=submission)

    if not submission.is_accessible_by(user) or user.profile.is_contest_account:
        raise Http404()

    if user.profile.current_contest is not None:
        return JsonResponse({})

    return JsonResponse({
        'source': submission.source.replace('\r', ''),
    })
