from operator import attrgetter

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import F, OuterRef, Prefetch, Q, Subquery
from django.http import Http404, JsonResponse
from django.utils.timezone import now
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView

from judge.models import Contest, ContestParticipation, ContestTag, Problem, Profile, Rating, Submission


def sane_time_repr(delta):
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    return '%02d:%02d:%02d' % (days, hours, minutes)


class JSONResponseMixin:
    def get_data(self, context):
        raise NotImplementedError()

    def get_error(self, exception):
        raise NotImplementedError()

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(
            self.get_data(context),
            **response_kwargs,
        )

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            return self.get_error(e)


class APIMixin(JSONResponseMixin):
    def get_object_data(self, obj):
        raise NotImplementedError()

    def get_api_data(self, context):
        raise NotImplementedError()

    def get_default_data(self, **kwargs):
        resp = {
            'api_version': '2.0',
            'method': self.request.method.lower(),
            'fetched': now().isoformat(),
        }
        resp.update(kwargs)
        return resp

    def get_data(self, context):
        return self.get_default_data(data=self.get_api_data(context))

    def get_error(self, exception):
        excepted_exceptions = {
            ValueError: (400, 'invalid filter value type'),
            PermissionDenied: (403, 'permission denied'),
            Http404: (404, 'page/object not found'),
        }
        exception_type = type(exception)
        if exception_type in excepted_exceptions:
            exception_data = excepted_exceptions[exception_type]
            return JsonResponse(
                self.get_default_data(error={
                    'code': exception_data[0],
                    'message': exception_data[1],
                }),
                status=exception_data[0],
            )
        else:
            raise exception


class APIListView(APIMixin, BaseListView):
    paginate_by = settings.DMOJ_API_PAGE_SIZE
    basic_filters = ()
    list_filters = ()

    def get_unfiltered_queryset(self):
        return super().get_queryset()

    def filter_queryset(self, queryset):
        for key, filter_name in self.basic_filters:
            if key in self.request.GET:
                # may raise ValueError, but is excepted in APIMixin
                queryset = queryset.filter(**{
                    filter_name: self.request.GET.get(key),
                })

        for key, filter_name in self.list_filters:
            if key in self.request.GET:
                # may raise ValueError, but is excepted in APIMixin
                queryset = queryset.filter(**{
                    filter_name + '__in': self.request.GET.getlist(key),
                })

        return queryset.distinct()

    def get_queryset(self):
        return self.filter_queryset(self.get_unfiltered_queryset())

    def get_api_data(self, context):
        page = context['page_obj']
        objects = context['object_list']
        return {
            'current_object_count': len(objects),
            'items_per_page': page.paginator.per_page,
            'total_objects': len(page.paginator.object_list),
            'page_index': page.number,
            'total_pages': page.paginator.num_pages,
            'objects': [self.get_object_data(obj) for obj in objects],
        }


class APIDetailView(APIMixin, BaseDetailView):
    def get_api_data(self, context):
        return {
            'object': self.get_object_data(context['object']),
        }


class APIContestList(APIListView):
    model = Contest
    list_filters = (
        ('tag', 'tags__name'),
    )

    def get_unfiltered_queryset(self):
        return Contest.get_visible_contests(self.request.user).prefetch_related(
            Prefetch('tags', queryset=ContestTag.objects.only('name'), to_attr='tag_list'))

    def get_object_data(self, contest):
        return {
            'key': contest.key,
            'name': contest.name,
            'start_time': contest.start_time.isoformat(),
            'end_time': contest.end_time.isoformat(),
            'time_limit': contest.time_limit and sane_time_repr(contest.time_limit),
            'tags': list(map(attrgetter('name'), contest.tag_list)),
        }


class APIContestDetail(APIDetailView):
    model = Contest
    slug_field = 'key'
    slug_url_kwarg = 'contest'

    def get_object(self, queryset=None):
        contest = super().get_object(queryset)
        if not contest.is_accessible_by(self.request.user):
            raise Http404()
        return contest

    def get_object_data(self, contest):
        in_contest = contest.is_in_contest(self.request.user)
        can_see_rankings = contest.can_see_scoreboard(self.request.user)
        if contest.hide_scoreboard and in_contest:
            can_see_rankings = False

        problems = list(contest.contest_problems.select_related('problem')
                        .defer('problem__description').order_by('order'))

        new_ratings_subquery = Rating.objects.filter(participation=OuterRef('pk'))
        old_ratings_subquery = (Rating.objects.filter(user=OuterRef('user__pk'),
                                                      contest__end_time__lt=OuterRef('contest__end_time'))
                                .order_by('-contest__end_time'))
        participations = (contest.users.filter(virtual=0, user__is_unlisted=False)
                          .annotate(new_rating=Subquery(new_ratings_subquery.values('rating')[:1]))
                          .annotate(old_rating=Subquery(old_ratings_subquery.values('rating')[:1]))
                          .prefetch_related('user__organizations')
                          .annotate(username=F('user__user__username'))
                          .order_by('-score', 'cumtime') if can_see_rankings else [])
        can_see_problems = (in_contest or contest.ended or contest.is_editable_by(self.request.user))

        return {
            'key': contest.key,
            'name': contest.name,
            'is_organization_private': contest.is_organization_private,
            'organizations': list(contest.organizations.values_list('id', flat=True)),
            'is_private': contest.is_private,
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
                    'old_rating': participation.old_rating,
                    'new_rating': participation.new_rating,
                    'is_disqualified': participation.is_disqualified,
                    'solutions': contest.format.get_problem_breakdown(participation, problems),
                } for participation in participations],
        }


class APIProblemList(APIListView):
    model = Problem
    list_filters = (
        ('group', 'group__full_name'),
    )

    def get_unfiltered_queryset(self):
        queryset = Problem.objects.select_related('group').defer('description')

        # TODO: replace with Problem.get_visible_problems() when method is made
        if not self.request.user.has_perm('see_private_problem'):
            filter = Q(is_public=True)
            if self.request.user.is_authenticated:
                filter |= Q(authors=self.request.profile)
                filter |= Q(curators=self.request.profile)
                filter |= Q(testers=self.request.profile)
            queryset = queryset.filter(filter)
            if not self.request.user.has_perm('see_organization_problem'):
                filter = Q(is_organization_private=False)
                if self.request.user.is_authenticated:
                    filter |= Q(organizations__in=self.request.profile.organizations.all())
                queryset = queryset.filter(filter)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if settings.ENABLE_FTS and 'search' in self.request.GET:
            query = ' '.join(self.request.GET.getlist('search')).strip()
            if query:
                queryset = queryset.search(query)
        return queryset

    def get_object_data(self, problem):
        return {
            'code': problem.code,
            'name': problem.name,
            'partial': problem.partial,
            'points': problem.points,
            'group': problem.group.full_name,
        }


class APIProblemDetail(APIDetailView):
    model = Problem
    slug_field = 'code'
    slug_url_kwarg = 'problem'

    def get_object(self, queryset=None):
        # unconditionally deny access in contests to avoid revealing authors, types, points, etc.
        if self.request.user.is_authenticated and self.request.profile.current_contest is not None:
            raise PermissionDenied()

        problem = super().get_object(queryset)
        if not problem.is_accessible_by(self.request.user):
            raise Http404()
        return problem

    def get_object_data(self, problem):
        return {
            'name': problem.name,
            'authors': list(problem.authors.values_list('user__username', flat=True)),
            'types': list(problem.types.values_list('full_name', flat=True)),
            'group': problem.group.full_name,
            'time_limit': problem.time_limit,
            'memory_limit': problem.memory_limit,
            'points': problem.points,
            'partial': problem.partial,
            'short_circuit': problem.short_circuit,
            'languages': list(problem.allowed_languages.values_list('key', flat=True)),
            'is_organization_private': problem.is_organization_private,
            'organizations': list(problem.organizations.values_list('id', flat=True)),
        }


class APIUserList(APIListView):
    model = Profile
    list_filters = (
        ('organization', 'organizations'),
    )

    def get_unfiltered_queryset(self):
        return Profile.objects.filter(is_unlisted=False).select_related('user')

    def get_object_data(self, profile):
        last_rating = profile.ratings.last()
        return {
            'username': profile.user.username,
            'points': profile.points,
            'performance_points': profile.performance_points,
            'problem_count': profile.problem_count,
            'rank': profile.display_rank,
            'rating': last_rating.rating if last_rating is not None else None,
            'volatility': last_rating.volatility if last_rating is not None else None,
        }


class APIUserDetail(APIDetailView):
    model = Profile
    slug_field = 'user__username'
    slug_url_kwarg = 'user'

    def get_object_data(self, profile):
        submissions = list(
            Submission.objects
            .filter(
                case_points=F('case_total'),
                user=profile,
                problem__is_public=True,
                problem__is_organization_private=False,
            )
            .values('problem').distinct()
            .values_list('problem__code', flat=True),
        )

        last_rating = profile.ratings.last()

        contest_history = []
        participations = ContestParticipation.objects.filter(
            user=profile,
            virtual=ContestParticipation.LIVE,
            contest__in=Contest.get_visible_contests(self.request.user),
            contest__end_time__lt=now(),
        )
        for contest_key, score, cumtime, rating, volatility in participations.values_list(
            'contest__key', 'score', 'cumtime', 'rating__rating', 'rating__volatility',
        ):
            contest_history.append({
                'key': contest_key,
                'score': score,
                'cumtime': cumtime,
                'rating': rating,
                'volatility': volatility,
            })

        return {
            'username': profile.user.username,
            'points': profile.points,
            'performance_points': profile.performance_points,
            'problem_count': profile.problem_count,
            'solved_problems': submissions,
            'rank': profile.display_rank,
            'rating': profile.rating,
            'organizations': list(profile.organizations.values_list('id', flat=True)),
            'contests': {
                'current_rating': last_rating.rating if last_rating is not None else None,
                'current_volatility': last_rating.volatility if last_rating is not None else None,
                'history': contest_history,
            },
        }


class APISubmissionList(APIListView):
    model = Submission
    list_filters = (
        ('username', 'user__user__username'),
        ('problem', 'problem__code'),
        ('language', 'language__key'),
        ('result', 'result'),
    )

    def get_unfiltered_queryset(self):
        # TODO: after Problem.get_visible_problems is made, show all submissions that a user can access
        visible_problems = Problem.objects.filter(is_public=True, is_organization_private=False)
        return (
            Submission.objects
            .filter(problem__in=visible_problems)
            .only('id', 'problem_id', 'problem__code', 'user__user__username', 'date',
                  'language__key', 'points', 'result')
        )

    def get_object_data(self, submission):
        return {
            'id': submission.id,
            'problem': submission.problem.code,
            'user': submission.user.user.username,
            'date': submission.date.isoformat(),
            'language': submission.language.key,
            'points': submission.points,
            'result': submission.result,
        }


class APISubmissionDetail(LoginRequiredMixin, APIDetailView):
    model = Submission
    slug_field = 'id'
    slug_url_kwarg = 'submission'

    def get_object(self, queryset=None):
        # unconditionally deny access in contest to avoid revealing points
        if self.request.profile.current_contest is not None:
            raise PermissionDenied()

        submission = super().get_object(queryset)
        profile = self.request.profile
        problem = submission.problem
        if self.request.user.has_perm('judge.view_all_submission'):
            return submission
        if submission.user_id == profile.id:
            return submission
        if problem.is_editable_by(profile):
            return submission
        if problem.is_public or problem.testers.filter(id=profile.id).exists():
            if Submission.objects.filter(user_id=profile.id, result='AC', problem_id=problem.id,
                                         points=problem.points).exists():
                return submission
        raise PermissionDenied()

    def get_object_data(self, submission):
        return {
            'id': submission.id,
            'problem': submission.problem.code,
            'user': submission.user.user.username,
            'date': submission.date.isoformat(),
            'time': submission.time,
            'memory': submission.memory,
            'points': submission.points,
            'language': submission.language.key,
            'status': submission.status,
            'result': submission.result,
            'case_points': submission.case_points,
            'case_total': submission.case_total,
            'cases': [
                {
                    'case_number': case['case'],
                    'status': case['status'],
                    'time': case['time'],
                    'memory': case['memory'],
                    'points': case['points'],
                    'total': case['total'],
                } for case in submission.test_cases.values('case', 'status', 'time', 'memory', 'points', 'total')
            ],
        }
