from operator import attrgetter

from django.db.models import Prefetch, F, Max
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404

from dmoj import settings
from judge.models import Contest, Problem, Profile, Submission, ContestTag, ContestParticipation
from judge.views.contests import contest_access_check, base_contest_ranking_list


def error(message):
    return JsonResponse({
        "error": message
    }, status=422)


def api_v2_user_info(request):
    """
    {
        "points": 100.0,
        "rating": 2452,
        "rank": "user",
        "organizations": [],
        "solved_problems": ["ccc14s4", ...],
        "attempted_problems": [
            {
                "code": "Hello, World!",
                "points": 1.0,
                "max_points": 2.0
            }
        ],
        "authored_problems": ["dmpg16s4"],
        "contest_history": [
            {
                "contest": {
                    "code": "halloween14",
                    "name": "Kemonomimi Party",
                    "tags": ["seasonal"],
                    "time_limit": null,
                    "start_time": "2014-10-31T04:00:00+00:00",
                    "end_time": "2014-11-10T05:00:00+00:00"
                },
                "rank": 1,
                "rating:": 1800
            },
            // ...
        ]
    }
   """
    username = request.GET['username']
    if not username:
        return error("username argument not provided")
    try:
        profile = Profile.objects.get(user__username=username)
    except Profile.DoesNotExist:
        return error("no such user")

    resp = {
        "points": profile.points,
        "rating": profile.rating,
        "rank": profile.display_rank,
        "organizations": list(profile.organizations.values_list('key', flat=True))
    }

    contest_history = []
    for participation in ContestParticipation.objects.filter(user=profile, virtual=0, contest__is_public=True):
        contest_obj = participation.contest

        contest_history.append({
            'contest': {
                'code': contest_obj.key,
                'name': contest_obj.name,
                'tags': list(contest_obj.tags.values_list('name', flat=True)),
                'time_limit': contest_obj.time_limit and contest_obj.time_limit.total_seconds(),
                'start_time': contest_obj.start_time.isoformat(),
                'end_time': contest_obj.end_time.isoformat(),
            },
            'rank': -1,
            'rating': -1,
        })

    resp['contest_history'] = contest_history

    solved_problems = []
    attempted_problems = []

    problem_data = (Submission.objects.filter(points__gt=0, user=profile, problem__is_public=True)
                    .annotate(max_pts=Max('points'))
                    .values_list('max_pts', 'problem__points', 'problem__code')
                    .distinct())
    for awarded_pts, max_pts, problem in problem_data:
        if awarded_pts == max_pts:
            solved_problems.append(problem)
        else:
            attempted_problems.append({
                'awarded': awarded_pts,
                'max': max_pts,
                'problem': problem
            })

    resp['solved_problems'] = solved_problems
    resp['attempted_problems'] = attempted_problems
    resp['authored_problems'] = list(Problem.objects.filter(authors=profile).values_list('code', flat=True))

    return JsonResponse(resp)
