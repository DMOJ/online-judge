from operator import attrgetter

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView

from judge.models import (
    Contest, ContestParticipation, ContestTag, Organization, Problem, ProblemType, Profile, Rating, Submission,
)
from judge.utils.raw_sql import use_straight_join


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
    @cached_property
    def _now(self):
        return timezone.now()

    def get_object_data(self, obj):
        raise NotImplementedError()

    def get_api_data(self, context):
        raise NotImplementedError()

    def get_base_response(self, **kwargs):
        resp = {
            'api_version': '2.0',
            'method': self.request.method.lower(),
            'fetched': self._now.isoformat(),
        }
        resp.update(kwargs)
        return resp

    def get_data(self, context):
        return self.get_base_response(data=self.get_api_data(context))

    def get_error(self, exception):
        excepted_exceptions = {
            ValueError: (400, 'invalid filter value type'),
            ValidationError: (400, 'invalid filter value type'),
            PermissionDenied: (403, 'permission denied'),
            Http404: (404, 'page/object not found'),
        }
        exception_type = type(exception)
        if exception_type in excepted_exceptions:
            exception_data = excepted_exceptions[exception_type]
            return JsonResponse(
                self.get_base_response(error={
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
                # May raise ValueError or ValidationError, but is excepted in APIMixin
                queryset = queryset.filter(**{
                    filter_name: self.request.GET.get(key),
                })

        for key, filter_name in self.list_filters:
            if key in self.request.GET:
                # May raise ValueError or ValidationError, but is excepted in APIMixin
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
            'objects_per_page': page.paginator.per_page,
            'total_objects': page.paginator.count,
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
        ('organization', 'organizations'),
    )

    def get_unfiltered_queryset(self):
        return (
            Contest.get_visible_contests(self.request.user)
            .prefetch_related(
                Prefetch(
                    'tags',
                    queryset=ContestTag.objects.only('name'),
                    to_attr='tag_list',
                ),
            )
            .order_by('end_time')
        )

    def get_object_data(self, contest):
        return {
            'key': contest.key,
            'name': contest.name,
            'start_time': contest.start_time.isoformat(),
            'end_time': contest.end_time.isoformat(),
            'time_limit': contest.time_limit and contest.time_limit.total_seconds(),
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
        can_see_problems = (in_contest or contest.ended or contest.is_editable_by(self.request.user))

        problems = list(
            contest.contest_problems
            .select_related('problem')
            .defer('problem__description')
            .order_by('order'),
        )

        new_ratings_subquery = Rating.objects.filter(participation=OuterRef('pk'))
        old_ratings_subquery = (
            Rating.objects
            .filter(user=OuterRef('user__pk'), contest__end_time__lt=OuterRef('contest__end_time'))
            .order_by('-contest__end_time')
        )
        participations = (
            contest.users
            .filter(virtual=ContestParticipation.LIVE, user__is_unlisted=False)
            .annotate(
                username=F('user__user__username'),
                old_rating=Subquery(old_ratings_subquery.values('rating')[:1]),
                new_rating=Subquery(new_ratings_subquery.values('rating')[:1]),
            )
            .order_by('-score', 'cumtime')
        )

        return {
            'key': contest.key,
            'name': contest.name,
            'start_time': contest.start_time.isoformat(),
            'end_time': contest.end_time.isoformat(),
            'time_limit': contest.time_limit and contest.time_limit.total_seconds(),
            'is_rated': contest.is_rated,
            'rate_all': contest.is_rated and contest.rate_all,
            'has_rating': contest.ratings.exists(),
            'rating_floor': contest.rating_floor,
            'rating_ceiling': contest.rating_ceiling,
            'is_organization_private': contest.is_organization_private,
            'organizations': list(contest.organizations.values_list('id', flat=True)),
            'is_private': contest.is_private,
            'tags': list(contest.tags.values_list('name', flat=True)),
            'format': {
                'name': contest.format_name,
                'config': contest.format_config,
                'problem_label_script': contest.problem_label_script,
            },
            'problems': [
                {
                    'points': int(problem.points),
                    'partial': problem.partial,
                    'is_pretested': problem.is_pretested and contest.run_pretests_only,
                    'max_submissions': problem.max_submissions or None,
                    'name': problem.problem.name,
                    'code': problem.problem.code,
                } for problem in problems
            ] if can_see_problems else [],
            'rankings': [
                {
                    'user': participation.username,
                    'score': participation.score,
                    'cumulative_time': participation.cumtime,
                    'old_rating': participation.old_rating,
                    'new_rating': participation.new_rating,
                    'is_disqualified': participation.is_disqualified,
                    'solutions': contest.format.get_problem_breakdown(participation, problems),
                } for participation in participations
            ] if can_see_rankings else [],
        }


class APIContestParticipationList(APIListView):
    model = ContestParticipation
    basic_filters = (
        ('contest', 'contest__key'),
        ('user', 'user__user__username'),
        ('is_disqualified', 'is_disqualified'),
        ('participation_number', 'virtual'),
    )

    def get_unfiltered_queryset(self):
        visible_contests = Contest.get_visible_contests(self.request.user)

        # Check which contest scoreboards the user can actually see.
        # "Contest.get_visible_contests" only gets which contests the user can *see*.
        # Conditions for participation scoreboard access:
        #   1. Contest has ended
        #   2. User is the organizer of the contest
        #   3. User is specified to be able to "view contest scoreboard"
        if not self.request.user.has_perm('judge.see_private_contest'):
            q = Q(end_time__lt=self._now)
            if self.request.user.is_authenticated:
                if self.request.user.has_perm('judge.edit_own_contest'):
                    q |= Q(organizers=self.request.profile)
                q |= Q(view_contest_scoreboard=self.request.profile)
            visible_contests = visible_contests.filter(q)

        return (
            ContestParticipation.objects
            .filter(virtual__gte=0, contest__in=visible_contests)
            .annotate(contest_key=F('contest__key'), username=F('user__user__username'))
            .order_by('id')
            .only('score', 'cumtime', 'is_disqualified', 'virtual')
        )

    def get_object_data(self, participation):
        return {
            'user': participation.username,
            'contest': participation.contest_key,
            'score': participation.score,
            'cumulative_time': participation.cumtime,
            'is_disqualified': participation.is_disqualified,
            'participation_number': participation.virtual,
        }


class APIProblemList(APIListView):
    model = Problem
    basic_filters = (
        ('partial', 'partial'),
    )
    list_filters = (
        ('group', 'group__full_name'),
        ('type', 'types__full_name'),
        ('organization', 'organizations'),
    )

    def get_unfiltered_queryset(self):
        queryset = (
            Problem.objects
            .select_related('group')
            .prefetch_related(
                Prefetch(
                    'types',
                    queryset=ProblemType.objects.only('full_name'),
                    to_attr='type_list',
                ),
            )
            .defer('description')
            .order_by('code')
        )

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
            'types': list(map(attrgetter('full_name'), problem.type_list)),
            'group': problem.group.full_name,
            'points': problem.points,
            'partial': problem.partial,
        }


class APIProblemDetail(APIDetailView):
    model = Problem
    slug_field = 'code'
    slug_url_kwarg = 'problem'

    def get_object(self, queryset=None):
        problem = super().get_object(queryset)
        if not problem.is_accessible_by(self.request.user, skip_contest_problem_check=True):
            raise Http404()
        return problem

    def get_object_data(self, problem):
        return {
            'code': problem.code,
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
        latest_rating_subquery = Rating.objects.filter(user=OuterRef('pk')).order_by('-contest__end_time')
        return (
            Profile.objects
            .filter(is_unlisted=False)
            .annotate(
                username=F('user__username'),
                latest_rating=Subquery(latest_rating_subquery.values('rating')[:1]),
                latest_volatility=Subquery(latest_rating_subquery.values('volatility')[:1]),
            )
            .order_by('id')
            .only('points', 'performance_points', 'problem_count', 'display_rank')
        )

    def get_object_data(self, profile):
        return {
            'username': profile.username,
            'points': profile.points,
            'performance_points': profile.performance_points,
            'problem_count': profile.problem_count,
            'rank': profile.display_rank,
            'rating': profile.latest_rating,
            'volatility': profile.latest_volatility,
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
                result='AC',
                user=profile,
                problem__is_public=True,
                problem__is_organization_private=False,
            )
            .values('problem').distinct()
            .values_list('problem__code', flat=True),
        )

        last_rating = profile.ratings.order_by('-contest__end_time').first()

        contest_history = []
        participations = (
            ContestParticipation.objects
            .filter(
                user=profile,
                virtual=ContestParticipation.LIVE,
                contest__in=Contest.get_visible_contests(self.request.user),
                contest__end_time__lt=self._now,
            )
            .order_by('contest__end_time')
        )
        for contest_key, score, cumtime, rating, volatility in participations.values_list(
            'contest__key', 'score', 'cumtime', 'rating__rating', 'rating__volatility',
        ):
            contest_history.append({
                'key': contest_key,
                'score': score,
                'cumulative_time': cumtime,
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
            'rating': last_rating.rating if last_rating is not None else None,
            'volatility': last_rating.volatility if last_rating is not None else None,
            'organizations': list(profile.organizations.values_list('id', flat=True)),
            'contests': contest_history,
        }


class APISubmissionList(APIListView):
    model = Submission
    list_filters = (
        ('user', 'user__user__username'),
        ('problem', 'problem__code'),
        ('language', 'language__key'),
        ('result', 'result'),
    )

    def get_unfiltered_queryset(self):
        # TODO: after Problem.get_visible_problems is made, show all submissions that a user can access
        visible_problems = Problem.objects.filter(is_public=True, is_organization_private=False)
        queryset = Submission.objects.all()
        use_straight_join(queryset)
        queryset = (
            queryset
            .filter(problem__in=visible_problems)
            .annotate(
                username=F('user__user__username'),
                problem_code=F('problem__code'),
                language_key=F('language__key'),
            )
            .order_by('id')
            .only('id', 'date', 'time', 'memory', 'points', 'result')
        )
        return queryset

    def get_object_data(self, submission):
        return {
            'id': submission.id,
            'problem': submission.problem_code,
            'user': submission.username,
            'date': submission.date.isoformat(),
            'language': submission.language_key,
            'time': submission.time,
            'memory': submission.memory,
            'points': submission.points,
            'result': submission.result,
        }


class APISubmissionDetail(LoginRequiredMixin, APIDetailView):
    model = Submission
    slug_field = 'id'
    slug_url_kwarg = 'submission'

    def get_object(self, queryset=None):
        submission = super().get_object(queryset)
        profile = self.request.profile
        problem = submission.problem

        if self.request.user.has_perm('judge.view_all_submission'):
            return submission
        if problem.is_editor(profile):
            return submission
        if not problem.is_accessible_by(self.request.user, skip_contest_problem_check=True):
            raise PermissionDenied()
        if submission.user_id == profile.id:
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


class APIOrganizationList(APIListView):
    model = Organization
    basic_filters = (
        ('is_open', 'is_open'),
    )

    def get_unfiltered_queryset(self):
        return Organization.objects.annotate(member_count=Count('member')).order_by('id')

    def get_object_data(self, organization):
        return {
            'id': organization.id,
            'slug': organization.slug,
            'short_name': organization.short_name,
            'is_open': organization.is_open,
            'member_count': organization.member_count,
        }
