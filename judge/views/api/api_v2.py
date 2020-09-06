from operator import attrgetter

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView

from judge.models import (
    Contest, ContestParticipation, ContestTag, Judge, Language, Organization, Problem, ProblemType, Profile, Rating,
    Submission,
)
from judge.utils.raw_sql import join_sql_subquery, use_straight_join
from judge.views.submission import group_test_cases


class APILoginRequiredException(Exception):
    pass


class APILoginRequiredMixin:
    def setup_api(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise APILoginRequiredException()
        super().setup_api(request, *args, **kwargs)


class APIMixin:
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
        caught_exceptions = {
            ValueError: (400, 'invalid filter value type'),
            ValidationError: (400, 'invalid filter value type'),
            PermissionDenied: (403, 'permission denied'),
            APILoginRequiredException: (403, 'login required'),
            Http404: (404, 'page/object not found'),
        }
        exception_type = type(exception)
        if exception_type in caught_exceptions:
            status_code, message = caught_exceptions[exception_type]
            return JsonResponse(
                self.get_base_response(error={
                    'code': status_code,
                    'message': message,
                }),
                status=status_code,
            )
        else:
            raise exception

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(
            self.get_data(context),
            **response_kwargs,
        )

    def setup_api(self, request, *args, **kwargs):
        pass

    def dispatch(self, request, *args, **kwargs):
        try:
            self.setup_api(request, *args, **kwargs)
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            return self.get_error(e)


class APIListView(APIMixin, BaseListView):
    paginate_by = settings.DMOJ_API_PAGE_SIZE
    basic_filters = ()
    list_filters = ()

    def get_unfiltered_queryset(self):
        return super().get_queryset()

    def filter_queryset(self, queryset):
        for key, filter_name in self.basic_filters:
            if key in self.request.GET:
                # May raise ValueError or ValidationError, but is caught in APIMixin
                queryset = queryset.filter(**{
                    filter_name: self.request.GET.get(key),
                })

        for key, filter_name in self.list_filters:
            if key in self.request.GET:
                # May raise ValueError or ValidationError, but is caught in APIMixin
                queryset = queryset.filter(**{
                    filter_name + '__in': self.request.GET.getlist(key),
                })

        return queryset

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
        can_see_rankings = contest.can_see_full_scoreboard(self.request.user)
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
            .order_by('-score', 'cumtime', 'tiebreaker')
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
            'hidden_scoreboard': contest.hide_scoreboard,
            'is_organization_private': contest.is_organization_private,
            'organizations': list(
                contest.organizations.values_list('id', flat=True) if contest.is_organization_private else [],
            ),
            'is_private': contest.is_private,
            'tags': list(contest.tags.values_list('name', flat=True)),
            'format': {
                'name': contest.format_name,
                'config': contest.format_config,
            },
            'problems': [
                {
                    'points': int(problem.points),
                    'partial': problem.partial,
                    'is_pretested': problem.is_pretested and contest.run_pretests_only,
                    'max_submissions': problem.max_submissions or None,
                    'label': contest.get_label_for_problem(index),
                    'name': problem.problem.name,
                    'code': problem.problem.code,
                } for index, problem in enumerate(problems)
            ] if can_see_problems else [],
            'rankings': [
                {
                    'user': participation.username,
                    'score': participation.score,
                    'cumulative_time': participation.cumtime,
                    'tiebreaker': participation.tiebreaker,
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
        ('virtual_participation_number', 'virtual'),
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
            .select_related('user__user', 'contest')
            .order_by('id')
            .only(
                'user__user__username',
                'contest__key',
                'score',
                'cumtime',
                'tiebreaker',
                'is_disqualified',
                'virtual',
            )
        )

    def get_object_data(self, participation):
        return {
            'user': participation.user.username,
            'contest': participation.contest.key,
            'score': participation.score,
            'cumulative_time': participation.cumtime,
            'tiebreaker': participation.tiebreaker,
            'is_disqualified': participation.is_disqualified,
            'virtual_participation_number': participation.virtual,
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
        return (
            Problem.get_visible_problems(self.request.user)
            .select_related('group')
            .prefetch_related(
                Prefetch(
                    'types',
                    queryset=ProblemType.objects.only('full_name'),
                    to_attr='type_list',
                ),
            )
            .order_by('code')
            .distinct()
        )

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
            'language_resource_limits': [
                {
                    'language': key,
                    'time_limit': time_limit,
                    'memory_limit': memory_limit,
                }
                for key, time_limit, memory_limit in
                problem.language_limits.values_list('language__key', 'time_limit', 'memory_limit')
            ],
            'points': problem.points,
            'partial': problem.partial,
            'short_circuit': problem.short_circuit,
            'languages': list(problem.allowed_languages.values_list('key', flat=True)),
            'is_organization_private': problem.is_organization_private,
            'organizations': list(
                problem.organizations.values_list('id', flat=True) if problem.is_organization_private else [],
            ),
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
            .filter(is_unlisted=False, user__is_active=True)
            .annotate(
                username=F('user__username'),
                latest_rating=Subquery(latest_rating_subquery.values('rating')[:1]),
                latest_volatility=Subquery(latest_rating_subquery.values('volatility')[:1]),
            )
            .order_by('id')
            .only('id', 'points', 'performance_points', 'problem_count', 'display_rank')
        )

    def get_object_data(self, profile):
        return {
            'id': profile.id,
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
        solved_problems = list(
            Submission.objects
            .filter(
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
            'id': profile.id,
            'username': profile.user.username,
            'points': profile.points,
            'performance_points': profile.performance_points,
            'problem_count': profile.problem_count,
            'solved_problems': solved_problems,
            'rank': profile.display_rank,
            'rating': last_rating.rating if last_rating is not None else None,
            'volatility': last_rating.volatility if last_rating is not None else None,
            'organizations': list(profile.organizations.values_list('id', flat=True)),
            'contests': contest_history,
        }


class APISubmissionList(APIListView):
    model = Submission
    basic_filters = (
        ('user', 'user__user__username'),
        ('problem', 'problem__code'),
    )
    list_filters = (
        ('language', 'language__key'),
        ('result', 'result'),
    )

    def get_unfiltered_queryset(self):
        queryset = Submission.objects.all()
        use_straight_join(queryset)
        join_sql_subquery(
            queryset,
            subquery=Problem.get_visible_problems(self.request.user).distinct().only('id').query,
            params=[],
            join_fields=[('problem_id', 'id')],
            alias='visible_problems',
        )
        return (
            queryset
            .select_related('problem', 'user__user', 'language')
            .order_by('id')
            .only(
                'id',
                'problem__code',
                'user__user__username',
                'date',
                'language__key',
                'time',
                'memory',
                'points',
                'result',
            )
        )

    def get_object_data(self, submission):
        return {
            'id': submission.id,
            'problem': submission.problem.code,
            'user': submission.user.user.username,
            'date': submission.date.isoformat(),
            'language': submission.language.key,
            'time': submission.time,
            'memory': submission.memory,
            'points': submission.points,
            'result': submission.result,
        }


class APISubmissionDetail(APILoginRequiredMixin, APIDetailView):
    model = Submission
    slug_field = 'id'
    slug_url_kwarg = 'submission'

    def get_object(self, queryset=None):
        submission = super().get_object(queryset)
        if not submission.can_see_detail(self.request.user):
            raise PermissionDenied()
        return submission

    def get_object_data(self, submission):
        cases = []
        for batch in group_test_cases(submission.test_cases.all())[0]:
            batch_cases = [
                {
                    'type': 'case',
                    'case_id': case.case,
                    'status': case.status,
                    'time': case.time,
                    'memory': case.memory,
                    'points': case.points,
                    'total': case.total,
                } for case in batch['cases']
            ]

            # These are individual cases.
            if batch['id'] is None:
                cases.extend(batch_cases)
            # This is one batch.
            else:
                cases.append({
                    'type': 'batch',
                    'batch_id': batch['id'],
                    'cases': batch_cases,
                    'points': batch['points'],
                    'total': batch['total'],
                })

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
            'cases': cases,
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


class APILanguageList(APIListView):
    model = Language
    basic_filters = (
        ('common_name', 'common_name'),
    )

    def get_object_data(self, language):
        return {
            'id': language.id,
            'key': language.key,
            'short_name': language.short_name,
            'common_name': language.common_name,
            'ace_mode_name': language.ace,
            'pygments_name': language.pygments,
            'code_template': language.template,
        }


class APIJudgeList(APIListView):
    model = Judge

    def get_unfiltered_queryset(self):
        return Judge.objects.filter(online=True).prefetch_related('runtimes').order_by('name')

    def get_object_data(self, judge):
        return {
            'name': judge.name,
            'start_time': judge.start_time.isoformat(),
            'ping': judge.ping_ms,
            'load': judge.load,
            'languages': list(judge.runtimes.values_list('key', flat=True)),
        }
