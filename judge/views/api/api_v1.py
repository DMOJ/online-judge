from operator import attrgetter

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, OuterRef, Prefetch, Subquery
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404

from dmoj import settings
from judge.models import Contest, ContestParticipation, ContestTag, Problem, Profile, Rating, Submission


def sane_time_repr(delta):
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    return '%02d:%02d:%02d' % (days, hours, minutes)


def api_v1_contest_list(request):
    queryset = Contest.get_visible_contests(request.user).prefetch_related(
        Prefetch('tags', queryset=ContestTag.objects.only('name'), to_attr='tag_list'))

    return JsonResponse({c.key: {
        'name': c.name,
        'start_time': c.start_time.isoformat(),
        'end_time': c.end_time.isoformat(),
        'time_limit': c.time_limit and sane_time_repr(c.time_limit),
        'labels': list(map(attrgetter('name'), c.tag_list)),
    } for c in queryset})


def api_v1_contest_detail(request, contest):
    contest = get_object_or_404(Contest, key=contest)

    if not contest.is_accessible_by(request.user):
        raise Http404()

    in_contest = contest.is_in_contest(request.user)
    can_see_rankings = contest.can_see_full_scoreboard(request.user)

    problems = list(contest.contest_problems.select_related('problem')
                    .defer('problem__description').order_by('order'))

    new_ratings_subquery = Rating.objects.filter(participation=OuterRef('pk'))
    old_ratings_subquery = (Rating.objects.filter(user=OuterRef('user__pk'),
                                                  contest__end_time__lt=OuterRef('contest__end_time'))
                            .order_by('-contest__end_time'))
    participations = (contest.users.filter(virtual=0)
                      .annotate(new_rating=Subquery(new_ratings_subquery.values('rating')[:1]))
                      .annotate(old_rating=Subquery(old_ratings_subquery.values('rating')[:1]))
                      .prefetch_related('user__organizations')
                      .annotate(username=F('user__user__username'))
                      .order_by('-score', 'cumtime', 'tiebreaker') if can_see_rankings else [])
    can_see_problems = (in_contest or contest.ended or contest.is_editable_by(request.user))

    return JsonResponse({
        'time_limit': contest.time_limit and contest.time_limit.total_seconds(),
        'start_time': contest.start_time.isoformat(),
        'end_time': contest.end_time.isoformat(),
        'tags': list(contest.tags.values_list('name', flat=True)),
        'is_rated': contest.is_rated,
        'rate_all': contest.is_rated and contest.rate_all,
        'has_rating': contest.ratings.exists(),
        'rating_floor': contest.rating_floor,
        'rating_ceiling': contest.rating_ceiling,
        'format': {
            'name': contest.format_name,
            'config': contest.format_config,
        },
        'problems': [
            {
                'points': int(problem.points),
                'partial': problem.partial,
                'name': problem.problem.name,
                'code': problem.problem.code,
            } for problem in problems] if can_see_problems else [],
        'rankings': [
            {
                'user': participation.username,
                'points': participation.score,
                'cumtime': participation.cumtime,
                'tiebreaker': participation.tiebreaker,
                'old_rating': participation.old_rating,
                'new_rating': participation.new_rating,
                'is_disqualified': participation.is_disqualified,
                'solutions': contest.format.get_problem_breakdown(participation, problems),
            } for participation in participations],
    })


def api_v1_problem_list(request):
    queryset = Problem.get_visible_problems(request.user)
    if settings.ENABLE_FTS and 'search' in request.GET:
        query = ' '.join(request.GET.getlist('search')).strip()
        if query:
            queryset = queryset.search(query)
    queryset = queryset.values_list('code', 'points', 'partial', 'name', 'group__full_name')

    return JsonResponse({code: {
        'points': points,
        'partial': partial,
        'name': name,
        'group': group,
    } for code, points, partial, name, group in queryset})


def api_v1_problem_info(request, problem):
    p = get_object_or_404(Problem, code=problem)
    if not p.is_accessible_by(request.user, skip_contest_problem_check=True):
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
    queryset = Profile.objects.filter(is_unlisted=False).values_list('user__username', 'points', 'performance_points',
                                                                     'display_rank')
    return JsonResponse({username: {
        'points': points,
        'performance_points': performance_points,
        'rank': rank,
    } for username, points, performance_points, rank in queryset})


def api_v1_user_info(request, user):
    profile = get_object_or_404(Profile, user__username=user)
    submissions = list(Submission.objects.filter(case_points=F('case_total'), user=profile, problem__is_public=True,
                                                 problem__is_organization_private=False)
                       .values('problem').distinct().values_list('problem__code', flat=True))
    resp = {
        'points': profile.points,
        'performance_points': profile.performance_points,
        'rank': profile.display_rank,
        'solved_problems': submissions,
        'organizations': list(profile.organizations.values_list('id', flat=True)),
    }

    last_rating = profile.ratings.last()

    contest_history = {}
    participations = ContestParticipation.objects.filter(user=profile, virtual=0, contest__is_visible=True,
                                                         contest__is_private=False,
                                                         contest__is_organization_private=False)
    for contest_key, rating, mean, performance in participations.values_list(
        'contest__key', 'rating__rating', 'rating__mean', 'rating__performance',
    ):
        contest_history[contest_key] = {
            'rating': rating,
            'raw_rating': mean,
            'performance': performance,
        }

    resp['contests'] = {
        'current_rating': last_rating.rating if last_rating else None,
        'history': contest_history,
    }

    return JsonResponse(resp)


def api_v1_user_submissions(request, user):
    profile = get_object_or_404(Profile, user__username=user)
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


def api_v1_user_ratings(request, page):
    queryset = Profile.objects.filter(is_unlisted=False, user__is_active=True).values_list('user__username', 'rating')
    paginator = Paginator(queryset, settings.DMOJ_API_PAGE_SIZE)

    try:
        page = paginator.page(int(page))
    except (PageNotAnInteger, EmptyPage):
        return JsonResponse({'error': 'page not found'}, status=422)
    except (KeyError, ValueError):
        return JsonResponse({'error': 'invalid page number'}, status=422)

    return JsonResponse({
        'pages': paginator.num_pages,
        'users': {
            username: {
                'rating': rating,
            } for username, rating in page
        },
    })
