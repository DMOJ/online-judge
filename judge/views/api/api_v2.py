from operator import attrgetter

from django.db.models import Max
from django.http import JsonResponse

from judge.models import ContestParticipation, Problem, Profile, Submission
from judge.utils.ranker import ranker
from judge.views.contests import contest_ranking_list


def error(message):
    return JsonResponse({'error': message}, status=422)


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
    try:
        username = request.GET['username']
    except KeyError:
        return error("no username passed")
    if not username:
        return error("username argument not provided")
    try:
        profile = Profile.objects.get(user__username=username)
    except Profile.DoesNotExist:
        return error("no such user")

    last_rating = list(profile.ratings.order_by('-contest__end_time'))

    resp = {
        "rank": profile.display_rank,
        "organizations": list(profile.organizations.values_list('key', flat=True)),
    }

    contest_history = []
    for participation in (ContestParticipation.objects.filter(user=profile, virtual=0, contest__is_visible=True)
                          .order_by('-contest__end_time')):
        contest = participation.contest

        problems = list(contest.contest_problems.select_related('problem').defer('problem__description')
                               .order_by('order'))
        rank, result = next(filter(lambda data: data[1].user == profile.user,
                                   ranker(contest_ranking_list(contest, problems),
                                          key=attrgetter('points', 'cumtime'))))

        contest_history.append({
            'contest': {
                'code': contest.key,
                'name': contest.name,
                'tags': list(contest.tags.values_list('name', flat=True)),
                'time_limit': contest.time_limit and contest.time_limit.total_seconds(),
                'start_time': contest.start_time.isoformat(),
                'end_time': contest.end_time.isoformat(),
            },
            'rank': rank,
            'rating': result.participation_rating,
        })

    resp['contests'] = {
        "current_rating": last_rating[0].rating if last_rating else None,
        "volatility": last_rating[0].volatility if last_rating else None,
        'history': contest_history,
    }

    solved_problems = []
    attempted_problems = []

    problem_data = (Submission.objects.filter(points__gt=0, user=profile, problem__is_public=True,
                                              problem__is_organization_private=False)
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
                'problem': problem,
            })

    resp['problems'] = {
        'points': profile.points,
        'solved': solved_problems,
        'attempted': attempted_problems,
        'authored': list(Problem.objects.filter(is_public=True, is_organization_private=False, authors=profile)
                         .values_list('code', flat=True)),
    }

    return JsonResponse(resp)
