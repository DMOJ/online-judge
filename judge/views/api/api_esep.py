# flake8: noqa

import json
from datetime import timedelta, datetime
from functools import partial
from operator import attrgetter

from django.http import StreamingHttpResponse
import zipfile
import io
from django.contrib.auth.models import AnonymousUser, User
from django.db.models.functions import TruncDate
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils.formats import date_format
from django.utils.safestring import mark_safe
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _


from judge.models import (
    Language, Problem, Profile, Submission, SubmissionSource, ContestParticipation, ProblemType, ContestSubmission,
    Organization, Solution, Contest, Ticket, TicketMessage
)
from django.db.models import F, Min, Max, Count, Prefetch, Q, Value, IntegerField
from django.contrib.contenttypes.models import ContentType

from judge.ratings import rating_class, rating_progress
from judge.views.api.api_v2 import APIListView, APIDetailView
from judge.views.contests import base_contest_ranking_list, get_contest_ranking_list
from judge.views.submission import group_test_cases

import requests

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

def get_cpfed_token(request):
    token = None
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split('Bearer ')[1]
    return token


@method_decorator(csrf_exempt, name='dispatch')
class APIProblemSubmit(View):
    def post(self, request, problem_code, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        source = request.POST.get('source')
        language_key = request.POST.get('language_key')
        username = request.POST.get('username')
        if not all([source, language_key, username]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        try:
            profile = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            return JsonResponse({'error': f'No such user {username}'}, status=404)

        try:
            problem = Problem.objects.get(code=problem_code)
        except Problem.DoesNotExist:
            return JsonResponse({'error': f'No such problem {problem_code}'}, status=404)

        try:
            language = Language.objects.get(key=language_key)
        except Language.DoesNotExist:
            return JsonResponse({'error': f'No such language {language_key}'}, status=404)

        try:
            from judge import event_poster as event
            submission = Submission.objects.create(user=profile, problem=problem, language=language)
            submission_source = SubmissionSource.objects.create(submission=submission, source=source)
            submission.judge(force_judge=True, judge_id=None)

            return JsonResponse({'submission_id': submission.id, 'last_msg': event.last()}, status=200)
        except Exception as e:
            return JsonResponse({'error': 'Internal server error occurred', 'details': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class APISubmissionDetailEsep(View):
    def get(self, request, submission_id, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return JsonResponse({'error': f'No such submission {submission_id}'}, status=404)

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

            if batch['id'] is None:
                cases.extend(batch_cases)
            else:
                cases.append({
                    'type': 'batch',
                    'batch_id': batch['id'],
                    'cases': batch_cases,
                    'points': batch['points'],
                    'total': batch['total'],
                })

        include_achievements = request.GET.get('include_achievements') == 'true'

        res = {
            'id': submission.id,
            'problem': submission.problem.code,
            'source': submission.source.source,
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
            'cases': cases
        }
        if include_achievements and submission.result == 'AC':
            is_first_submit = self.is_first_submit(submission)
            res.update({
                'is_first_submit': is_first_submit
            })

            is_first_ac = self.is_first_ac(submission)
            if is_first_ac:
                is_ac_on_first_try = self.is_ac_on_first_try(submission)
                is_mini_streak = self.is_mini_streak(submission)
                is_corrected_solution = self.is_corrected_solution(submission)
                is_first_medium = self.is_first_medium(submission)
                problem_types = [problem_type.name for problem_type in submission.problem.types.all()]

                res.update({
                    'is_first_ac': is_first_ac,
                    'is_ac_on_first_try': is_ac_on_first_try,
                    'is_mini_streak': is_mini_streak,
                    'is_corrected_solution': is_corrected_solution,
                    'is_first_medium': is_first_medium,
                    'problem_types': problem_types,
                })

        return JsonResponse(res, status=200)

    def is_first_ac(self, submission):
        is_ac_before = Submission.objects.filter(
            user=submission.user,
            problem=submission.problem,
            result='AC',
            id__lt=submission.id
        ).exists()

        return not is_ac_before and submission.result == 'AC'

    def is_ac_on_first_try(self, submission):
        attempts_count = Submission.objects.filter(
            user=submission.user,
            problem=submission.problem,
            id__lte=submission.id
        ).count()

        return attempts_count == 1 and submission.result == 'AC'

    def is_mini_streak(self, submission):
        thirty_mins_ago = timezone.now() - timedelta(minutes=30)
        recent_submissions = Submission.objects.filter(
            user=submission.user,
            result='AC',
            date__gte=thirty_mins_ago
        ).values("problem__code").distinct().count()
        return recent_submissions >= 3 and submission.result == 'AC'

    def is_corrected_solution(self, submission):
        attempts_before = Submission.objects.filter(
            user=submission.user,
            problem=submission.problem,
            id__lt=submission.id
        ).count()
        return 1 <= attempts_before <= 4 and submission.result == 'AC'

    def is_first_submit(self, submission):
        attempts_before = Submission.objects.filter(
            user=submission.user
        ).count()
        return attempts_before == 1

    def is_first_medium(self, submission):
        if not submission.problem.group or submission.problem.group.name != 'medium':
            return False

        return Submission.objects.filter(
            result='AC',
            user=submission.user,
            problem__group__name='medium',
        ).count() == 1


@method_decorator(csrf_exempt, name='dispatch')
class APIUserListEsep(APIListView):
    model = Profile
    list_filters = (
        ('id', 'id'),
        ('organization', 'organizations'),
    )

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size', '10')
        try:
            page_size = int(page_size)
            return min(max(page_size, 10), 50)
        except ValueError:
            return 10

    def get_unfiltered_queryset(self):
        queryset = (
            Profile.objects
            .filter(is_unlisted=False, user__is_active=True)
            .annotate(username=F('user__username'))
            .only('id', 'points', 'performance_points', 'problem_count', 'display_rank', 'rating')
        )

        username_param = self.request.GET.get('username')
        if username_param:
            queryset = queryset.filter(user__username__istartswith=username_param)

        sort_by = self.request.GET.get('sort', '-rating')
        if sort_by == 'rating':
            queryset = queryset.order_by(F('rating').asc(nulls_last=True))
        else:
            queryset = queryset.order_by('-rating')

        return queryset

    def get_object_data(self, profile):
        return {
            'username': profile.username,
            'rating': profile.rating,
        }

    def get(self, request, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)
        return super().get(request, *args, **kwargs)


class APIUserDetailEsep(APIDetailView):
    model = Profile
    slug_field = 'user__username'
    slug_url_kwarg = 'user'

    def get_object_data(self, profile):
        rating_value = profile.rating
        rating_rank = None

        if rating_value:
            rating_rank = Profile.objects.filter(
                is_unlisted=False, rating__gt=rating_value,
            ).count() + 1

        aggregation_data = profile.ratings.aggregate(min_rating=Min('rating'), max_rating=Max('rating'), contests=Count('contest'))
        min_rating = aggregation_data.get('min_rating')
        max_rating = aggregation_data.get('max_rating')
        contests = aggregation_data.get('contests')

        ratings = profile.ratings.order_by('-contest__end_time').select_related('contest') \
            .defer('contest__description')

        rating_data = [{
            'label': rating.contest.name,
            'rating': rating.rating,
            'ranking': rating.rank,
            'link': '%s#!%s' % (reverse('contest_ranking', args=(rating.contest.key,)), profile.user.username),
            'timestamp': (rating.contest.end_time - EPOCH).total_seconds() * 1000,
            'date': date_format(timezone.localtime(rating.contest.end_time), _('M j, Y, G:i')),
            'class': rating_class(rating.rating),
            'height': '%.3fem' % rating_progress(rating.rating),
            'score': ContestParticipation.objects.get(contest=rating.contest, user=profile, virtual=0).score
        } for rating in ratings]

        submissions = (
            profile.submission_set
            .annotate(date_only=TruncDate('date'))
            .values('date_only').annotate(cnt=Count('id'))
        )

        submission_data = {
            date_counts['date_only'].isoformat(): date_counts['cnt'] for date_counts in submissions
        }

        return {
            'id': profile.id,
            'username': profile.user.username,
            'rating': rating_value,
            'rating_rank': rating_rank,
            'min_rating': min_rating,
            'max_rating': max_rating,
            'contests': contests,
            'problem_count': profile.problem_count,
            'rating_data': rating_data,
            'submission_data': submission_data
        }


class APIProblemListEsep(APIListView):
    model = Problem
    basic_filters = (
        ('partial', 'partial'),
    )
    list_filters = (
        ('type', 'types__name'),
    )

    def get_unfiltered_queryset(self):
        return (
            Problem.get_visible_problems(self.request.user)
            .select_related('group')
            .prefetch_related(
                Prefetch(
                    'types',
                    queryset=ProblemType.objects.only('name'),
                    to_attr='type_list',
                ),
            )
            .order_by('id')
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
        username = self.kwargs.get('username')

        data = {
            'code': problem.code,
            'name': problem.name,
            'types': list(map(attrgetter('name'), problem.type_list)),
            'group': problem.group.full_name,
            'ac_rate': problem.ac_rate,
            'is_organization_private': problem.is_organization_private,
            'is_public': problem.is_public,
        }
        if username:
            try:
                profile = Profile.objects.get(user__username=username)
                is_solved = Submission.objects.filter(user=profile, problem=problem, result='AC', case_points__gte=F('case_total')).exists()
                if is_solved:
                    data.update({
                        'user_status': 'AC'
                    })
                else:
                    submissions = Submission.objects.filter(user=profile, problem=problem).order_by('-judged_date')
                    if submissions.exists():
                        last_submission = submissions.first()
                        data.update({
                            'user_status': last_submission.result
                        })
                    else:
                        data.update({
                            'user_status': 'N'
                        })
            except Exception as e:
                pass

        return data


@method_decorator(csrf_exempt, name='dispatch')
class APIProblemTypeProgress(APIListView):
    def get(self, request, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        names_param = request.query_params.get('names', '')
        names = [name.strip() for name in names_param.split(',') if name.strip()]

        if not isinstance(names, list):
            return JsonResponse({'error': 'names must be a list'}, status=400)

        if not names:
            return JsonResponse({'error': 'names list cannot be empty'}, status=400)

        username = request.GET.get('username')
        if not username:
            return JsonResponse({'error': 'Missing username'}, status=400)

        try:
            profile = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            return JsonResponse({'error': f'No such user {username}'}, status=404)


class APIProblemTypeProgressList(APIListView):
    model = ProblemType

    list_filters = (
        ('type', 'name'),
    )

    def get_unfiltered_queryset(self):
        queryset = ProblemType.objects.all()

        username = self.kwargs.get('username')

        if username:
            try:
                profile = Profile.objects.get(user__username=username)
            except Profile.DoesNotExist:
                return ProblemType.objects.none()
        else:
            profile = None

        if profile:
            queryset = queryset.annotate(
                total_problems=Count('problem', distinct=True)
            )

            queryset = queryset.annotate(
                solved_problems=Count(
                    'problem',
                    filter=Q(
                        problem__submission__user=profile,
                        problem__submission__result='AC',
                        problem__submission__case_points__gte=F('problem__submission__case_total')
                    ),
                    distinct=True
                )
            )
        else:
            queryset = queryset.annotate(
                total_problems=Count('problem', distinct=True),
                solved_problems=Value(0, output_field=IntegerField())
            )

        return queryset

    def get_object_data(self, problem_type):
        data = {
            'name': problem_type.name,
            'total_problems': problem_type.total_problems,
        }

        if hasattr(problem_type, 'solved_problems'):
            data['solved_problems'] = problem_type.solved_problems
            data['total_problems'] = problem_type.total_problems

        return data


class APIDownloadContestSubmissons(View):
    def get(self, request):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        contest_key = request.GET.get('contest_key')
        if not contest_key:
            return JsonResponse({'error': 'contest_key must be provided'}, status=400)

        contest_submissions = ContestSubmission.objects.filter(
            participation__contest__key=contest_key,
            participation__virtual=0
        ).select_related(
            'submission__user__user',
            'submission__source',
            'submission__problem',
            'submission__language',
        ).values(
            'submission__user__user__username',
            'submission__language__extension',
            'submission__source__source',
            'submission__problem__code',
            'submission__id',
            'submission__result'
        ).iterator(chunk_size=100)

        def generate_zip():
            buffer = io.BytesIO()

            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for contest_submission in contest_submissions:
                    username = contest_submission['submission__user__user__username']
                    extension = contest_submission['submission__language__extension']
                    problem_code = contest_submission['submission__problem__code']
                    source_code = contest_submission['submission__source__source']
                    submission_id = contest_submission['submission__id']
                    submission_result = contest_submission['submission__result']
                    filename = f"{username}-{problem_code}-{submission_id}-{submission_result}.{extension}"

                    zip_file.writestr(filename, source_code.encode('utf-8'))

            buffer.seek(0)
            yield buffer.read()

        response = StreamingHttpResponse(
            generate_zip(),
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename={contest_key}_submissions.zip'

        return response


class APIHasSubmissionPermission(View):
    def get(self, request, submission_id, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)
        username = request.GET.get('username')
        if not username:
            return JsonResponse({'error': 'Username parameter is required'}, status=400)

        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return JsonResponse({'error': f'No such submission {submission_id}'}, status=404)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'error': f'No such user {username}'}, status=404)

        if submission.can_see_detail(user):
            return JsonResponse({}, status=200)
        return JsonResponse({'error': 'Permission denied'}, status=403)


@method_decorator(csrf_exempt, name='dispatch')
class APISyncUsersWithEsep(View):
    def post(self, request, *args, **kwargs):
        try:
            token = get_cpfed_token(request)
            if not token or token != settings.CPFED_TOKEN:
                return JsonResponse({'error': 'Unauthorized access'}, status=401)

            data = json.loads(request.body)

            org_id = data.get('org_id')
            emails = data.get('emails')
            usernames = data.get('usernames')

            if not all([org_id, emails, usernames]):
                return JsonResponse(
                    {'detail': 'Missing required parameters.'}, status=400,
                )
            if len(usernames) != len(emails):
                return JsonResponse(
                    {'detail': 'Usernames and emails length is not same.'}, status=400,
                )

            org = get_object_or_404(Organization, id=int(org_id))
            for user_email, username in zip(emails, usernames):
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    user = User.objects.create(username=username, email=user_email)
                profile, _ = Profile.objects.get_or_create(user=user, defaults={
                    'language': Language.objects.get(key=settings.DEFAULT_USER_LANGUAGE),
                    'is_banned_from_problem_voting': True
                })
                profile.organizations.add(org)

            return JsonResponse({'detail': 'Users added to org successfully'}, status=201)
        except Exception as e:
            return JsonResponse({'detail': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class APIRegisterUserFromCpfed(View):
    def post(self, request, *args, **kwargs):
        try:
            token = get_cpfed_token(request)
            if not token or token != settings.CPFED_TOKEN:
                return JsonResponse({'error': 'Unauthorized access'}, status=401)

            data = json.loads(request.body)

            email = data.get('email')
            username = data.get('username')
            if not username or not email:
                return JsonResponse({'error': 'username and email must be provided'}, status=400)

            user, created = User.objects.get_or_create(username=username, defaults={"email": email, "is_active": True})
            if not created:
                raise Exception("User already exists")
            profile = Profile.objects.get_or_create(user=user, defaults={
                'language': Language.objects.get(key=settings.DEFAULT_USER_LANGUAGE),
                'is_banned_from_problem_voting': True
            })[0]

            user.set_unusable_password()
            user.save()

            return JsonResponse({'detail': 'User registered to esep'}, status=201)
        except Exception as e:
            return JsonResponse({'detail': str(e)}, status=400)


class APIProblemEditorial(View):
    def get(self, request, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)
        code = request.GET.get('code')
        if not code:
            return JsonResponse({'error': 'code is required'}, status=400)

        try:
            solution = Solution.objects.get(problem__code=code, is_public=True)
            return JsonResponse({
                'content': solution.content,
                'created_at': solution.publish_on
            }, status=200)
        except Solution.DoesNotExist:
            return JsonResponse({'error': f'No editorial or problem with {code}'}, status=404)


def _format_standings_time(seconds):
    if seconds is None:
        return None
    seconds = int(seconds)
    return f'{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}'


def _serialize_standings_row(rank, ranking_profile, contest_problems):
    data = (ranking_profile.participation.format_data or {})
    scores = []
    for cp in contest_problems:
        cell = data.get(str(cp.id))
        if cell:
            scores.append({
                'code': cp.problem.code,
                'points': cell.get('points'),
                'time': _format_standings_time(cell.get('time')),
                'penalty': cell.get('penalty', 0),
                'frozen': bool(cell.get('frozen', False)),
            })
        else:
            scores.append({
                'code': cp.problem.code,
                'points': None,
                'time': None,
                'penalty': 0,
                'frozen': False,
            })
    profile = ranking_profile.participation.user
    rating = profile.rating
    return {
        'rank': rank,
        'user_id': ranking_profile.id,
        'username': ranking_profile.username,
        'rating': rating,
        'rating_tier': rating_class(rating) if rating is not None else None,
        'scores': scores,
        'total': {
            'points': ranking_profile.points,
            'time': _format_standings_time(ranking_profile.cumtime),
        },
    }


def compute_standings(contest_key, username=None):
    contest = Contest.objects.get(key=contest_key)

    profile = None
    if username:
        profile = Profile.objects.select_related('user').get(user__username=username)

    viewer = profile.user if profile else AnonymousUser()
    can_see_full = contest.can_see_full_scoreboard(viewer)

    if can_see_full:
        users, problems = get_contest_ranking_list(
            None, contest, show_current_virtual=False,
        )
    elif profile is not None:
        queryset = contest.users.filter(user=profile, virtual=ContestParticipation.LIVE)
        users, problems = get_contest_ranking_list(
            None, contest,
            ranking_list=partial(base_contest_ranking_list, queryset=queryset),
            show_current_virtual=False,
            ranker=lambda items, key: (('???', item) for item in items),
        )
    else:
        problems = list(
            contest.contest_problems.select_related('problem')
            .defer('problem__description').order_by('order'),
        )
        users = []

    rows = [_serialize_standings_row(rank, p, problems) for rank, p in users]

    return {
        'contest': {
            'key': contest.key,
            'name': contest.name,
            'format': contest.format_name,
            'start_time': contest.start_time.isoformat() if contest.start_time else None,
            'end_time': contest.end_time.isoformat() if contest.end_time else None,
        },
        'problems': [
            {
                'code': cp.problem.code,
                'name': cp.problem.name,
                'order': cp.order,
                'points': cp.points,
            }
            for cp in problems
        ],
        'can_see_full_scoreboard': can_see_full,
        'rows': rows,
    }


class APIContestUserProblemSubmissions(View):
    """List submissions for one user on one problem within a contest.

    Source code is intentionally NOT included; use the existing submission
    detail endpoint (with its own permission gate) for full content.
    """

    def get(self, request, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        contest_key = request.GET.get('contest_key')
        username = request.GET.get('username')
        problem_code = request.GET.get('problem_code')
        viewer_username = request.GET.get('viewer')
        if not contest_key or not username or not problem_code:
            return JsonResponse(
                {'error': 'contest_key, username and problem_code are required'},
                status=400,
            )

        try:
            contest = Contest.objects.get(key=contest_key)
        except Contest.DoesNotExist:
            return JsonResponse({'error': f'No such contest with {contest_key}'}, status=404)

        try:
            profile = Profile.objects.select_related('user').get(user__username=username)
        except Profile.DoesNotExist:
            return JsonResponse({'error': f'No such user {username}'}, status=404)

        try:
            problem = Problem.objects.get(code=problem_code)
        except Problem.DoesNotExist:
            return JsonResponse({'error': f'No such problem {problem_code}'}, status=404)

        viewer = AnonymousUser()
        if viewer_username:
            try:
                viewer = User.objects.get(username=viewer_username)
            except User.DoesNotExist:
                return JsonResponse({'error': f'No such viewer {viewer_username}'}, status=404)

        if not contest.can_see_full_scoreboard(viewer) and (
            not viewer.is_authenticated or viewer.username != username
        ):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        submissions = (
            Submission.objects
            .filter(contest_object=contest, user=profile, problem=problem)
            .select_related('language', 'problem', 'contest_object')
            .order_by('-id')
        )

        return JsonResponse({
            'submissions': [
                {
                    'id': sub.id,
                    'date': sub.date.isoformat() if sub.date else None,
                    'time': sub.time,
                    'memory': sub.memory,
                    'points': sub.points,
                    'case_points': sub.case_points,
                    'case_total': sub.case_total,
                    'status': sub.status,
                    'result': sub.result,
                    'language': sub.language.key if sub.language_id else None,
                    'can_see_detail': sub.can_see_detail(viewer),
                }
                for sub in submissions
            ],
        }, status=200)

class APIContestProblems(View):
    def get(self, request, contest_key, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        try:
            contest = Contest.objects.get(key = contest_key)
        except Contest.DoesNotExist:
            return JsonResponse({'error': f'No such contest {contest_key}'}, status=404)

        username = request.GET.get('username')
        profile = None
        if username:
            try:
                profile = Profile.objects.get(user__username = username)
            except Profile.DoesNotExist:
                pass

        if contest.is_organization_private:
            if profile is None:
                return JsonResponse({'error': 'Username required for private contest'}, status=400)
            in_org = profile.organizations.filter(
                id__in = contest.organizations.values('id'),
            ).exists()
            if not in_org:
                return JsonResponse({'error': 'You are not a member of of the contest organization'}, status=403)
        else:
            if not contest.ended:
                return JsonResponse({'error': 'Contest problems are available only after the contest ends'}, status=403)

        contest_problems = (
            contest.contest_problems
            .select_related('problem','problem__group')
            .prefetch_related(
                Prefetch(
                    'problem__types',
                    queryset=ProblemType.objects.only('name'),
                    to_attr='type_list',
                ),
            )
            .defer('problem__description')
            .order_by('order')
        )

        problems = []
        for index, cp in enumerate(contest_problems):
            p = cp.problem

            data = {
                'label': contest.get_label_for_problem(index),
                'order': cp.order,
                'points': int(cp.points),
                'partial': cp.partial,
                'is_pretested': cp.is_pretested,
                'max_submissions': cp.max_submissions or None,
                'code': p.code,
                'name': p.name,
                'time_limit': p.time_limit,
                'memory_limit': p.memory_limit,
                'ac_rate': p.ac_rate,
                'types': [t.name for t in p.type_list],
                'group': p.group.full_name if p.group else None,
            }

            if profile:
                is_solved = Submission.objects.filter(
                    user=profile, problem=p, result='AC',
                    case_points__gte=F('case_total'),
                ).exists()
                if is_solved:
                    data['user_status'] = 'AC'
                else:
                    last = (
                        Submission.objects
                        .filter(user=profile, problem=p)
                        .order_by('-judged_date')
                        .first()
                    )
                    data['user_status'] = last.result if last else 'N'
            problems.append(data)

        return JsonResponse({
            'contest': {
                'key': contest.key,
                'name': contest.name,
                'start_time': contest.start_time.isoformat() if contest.start_time else None,
                'end_time': contest.end_time.isoformat() if contest.end_time else None,
                'time_limit': contest.time_limit.total_seconds() if contest.time_limit else None,
                'format_name': contest.format_name,
                'is_organization_private': contest.is_organization_private,
            },
            'problems': problems,
        }, status=200)

@method_decorator(csrf_exempt, name='dispatch')
class APIContestGrantAccess(View):
    """Добавить пользователей во все организации контеста.

    Server-to-server операция: cpfed-web вызывает её от имени админа,
    чтобы дать списку юзеров доступ к organization-private контесту.
    """

    def post(self, request, contest_key, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        try:
            contest = Contest.objects.get(key=contest_key)
        except Contest.DoesNotExist:
            return JsonResponse({'error': f'No such contest {contest_key}'}, status=404)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        usernames = data.get('usernames')
        if not isinstance(usernames, list) or not usernames:
            return JsonResponse({'error': 'usernames must be a non-empty list'}, status=400)

        organizations = list(contest.organizations.all())
        if not organizations:
            return JsonResponse(
                {'error': 'Contest has no associated organizations; cannot grant access'},
                status=400,
            )

        added = []
        not_found = []

        for username in usernames:
            try:
                profile = Profile.objects.get(user__username=username)
            except Profile.DoesNotExist:
                not_found.append(username)
                continue

            for org in organizations:
                profile.organizations.add(org)

            added.append(username)

        return JsonResponse({
            'contest': contest.key,
            'organizations': [
                {'id': org.id, 'slug': org.slug, 'name': org.name}
                for org in organizations
            ],
            'added': added,
            'not_found': not_found,
        }, status=200)

@method_decorator(csrf_exempt, name = 'dispatch')
class APIProblemTickets(View):
    def get(self, request, problem_code, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status = 401)

        try:
            problem = Problem.objects.get(code = problem_code)
        except Problem.DoesNotExist:
            return JsonResponse({'error': f'No such problem {problem_code}'}, status=404)

        username = request.GET.get('username')
        if not username:
            return JsonResponse({'error': 'Username required'}, status=400)

        try:
            profile = Profile.objects.get(user__username = username)
        except Profile.DoesNotExist:
            return JsonResponse({'error': f'No such user {username}'}, status = 404)

        is_curator = False
        contest_key = request.GET.get('contest')
        if contest_key:
            try:
                contest = Contest.objects.get(key = contest_key)
                is_curator = (
                    contest.authors.filter(id=profile.id).exists()
                    or contest.curators.filter(id=profile.id).exists()
                    or contest.testers.filter(id=profile.id).exists()
                )
            except Contest.DoesNotExist:
                pass

        problem_ct = ContentType.objects.get_for_model(Problem)
        tickets_qs = Ticket.objects.filter(
            content_type = problem_ct,
            object_id = problem.id,
        )

        if not is_curator:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        tickets_qs = (
            tickets_qs
            .select_related('user__user')
            .prefetch_related('messages')
            .order_by('-time')
        )

        tickets = []
        for t in tickets_qs:
            messages_list = list(t.messages.order_by('time'))
            last = messages_list[-1] if messages_list else None

            ticket_data = {
                'id': t.id,
                'title': t.title,
                'time': t.time.isoformat(),
                'is_open': t.is_open,
                'author': t.user.user.username,
                'message_count': len(messages_list),
                'last_message_time': last.time.isoformat() if last else t.time.isoformat(),
            }

            if is_curator:
                ticket_data['messages'] = [
                    {
                        'id': m.id,
                        'body': m.body,
                        'time': m.time.isoformat(),
                        'author': m.user.user.username,
                        'is_mine': (m.user_id == profile.id),
                    }
                    for m in messages_list
                ]

            tickets.append(ticket_data)

        return JsonResponse({
            'problem': {
                'code': problem.code,
                'name': problem.name,
            },
            'is_curator': is_curator,
            'tickets': tickets
        }, status = 200)

    def post(self, request, problem_code, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        try:
            problem = Problem.objects.get(code = problem_code)
        except Problem.DoesNotExist:
            return JsonResponse({'error': f'No such problem {problem_code}'}, status=404)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        username = data.get('username')
        body = data.get('body')
        title = data.get('title')

        if not username:
            return JsonResponse({'error': 'Username is required'}, status=400)
        if not body:
            return JsonResponse({'error': 'Body is required'}, status=400)

        try:
            profile = Profile.objects.get(user__username = username)
        except Profile.DoesNotExist:
            return JsonResponse({'error': f'No such user {username}'}, status=404)

        if not title:
            title = f'Вопрос по задаче {problem.name}'[:100]

        ticket = Ticket.objects.create(
            title = title,
            user = profile,
            content_type = ContentType.objects.get_for_model(Problem),
            object_id = problem.id,
        )

        message = TicketMessage.objects.create(
            ticket = ticket,
            user = profile,
            body = body,
        )

        return JsonResponse({
            'ticket': {
                'id': ticket.id,
                'title': ticket.title,
                'time': ticket.time.isoformat(),
                'is_open': ticket.is_open,
                'author': profile.user.username,
            },
            'message': {
                'id': message.id,
                'body': message.body,
                'time': message.time.isoformat(),
                'author': profile.user.username,
            },
        }, status=201)

class APITicketDetail(View):
    def get(self, request, ticket_id, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token!=settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        try:
            ticket = Ticket.objects.select_related('user__user').get(id = ticket_id)
        except Ticket.DoesNotExist:
            return JsonResponse({'error': f'No such ticket {ticket_id}'}, status=404)

        username = request.GET.get('username')
        if not username:
            return JsonResponse({'error': 'Username required'}, status=400)

        try:
            profile = Profile.objects.get(user__username = username)
        except Profile.DoesNotExist:
            return JsonResponse({'error': f'No such user {username}'}, status=404)

        is_author = (ticket.user_id == profile.id)
        is_curator = False

        contest_key = request.GET.get('contest')
        if contest_key:
            try:
                contest = Contest.objects.get(key = contest_key)
                is_curator = (
                    contest.authors.filter(id=profile.id).exists()
                    or contest.curators.filter(id=profile.id).exists()
                    or contest.testers.filter(id=profile.id).exists()
                )
            except Contest.DoesNotExist:
                pass

        if not (is_author or is_curator):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        messages = (
            ticket.messages
            .select_related('user__user')
            .order_by('time')
        )

        messages_list = [
            {
                'id': m.id,
                'body': m.body,
                'time': m.time.isoformat(),
                'author': m.user.user.username,
                'is_mine': (m.user_id == profile.id)
            }
            for m in messages
        ]

        problem_info = None
        if isinstance(ticket.linked_item, Problem):
            problem_info = {
                'code': ticket.linked_item.code,
                'name': ticket.linked_item.name,
            }

        return JsonResponse({
            'ticket': {
                'id': ticket.id,
                'title': ticket.title,
                'time': ticket.time.isoformat(),
                'is_open': ticket.is_open,
                'author': ticket.user.user.username,
                'is_author': is_author,
            },
            'problem': problem_info,
            'messages': messages_list,
            'is_curator': is_curator,
        }, status=200)

@method_decorator(csrf_exempt, name='dispatch')
class APITicketMessages(View):
    def post(self, request, ticket_id, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        try:
            ticket = Ticket.objects.select_related('user__user').get(id=ticket_id)
        except Ticket.DoesNotExist:
            return JsonResponse({'error': f'No such ticket {ticket_id}'}, status=404)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        username = data.get('username')
        body = data.get('body')
        contest_key = data.get('contest_key')

        if not username or not body:
            return JsonResponse({'error': 'username and body required'}, status=400)

        try:
            profile = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            return JsonResponse({'error': f'No such user {username}'}, status=404)

        is_author = (ticket.user_id == profile.id)
        is_curator = False
        if contest_key:
            try:
                contest = Contest.objects.get(key=contest_key)
                is_curator = (
                    contest.authors.filter(id=profile.id).exists()
                    or contest.curators.filter(id=profile.id).exists()
                    or contest.testers.filter(id=profile.id).exists()
                )
            except Contest.DoesNotExist:
                pass

        if not (is_author or is_curator):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        if not ticket.is_open and not is_curator:
            return JsonResponse({'error': 'Ticket is closed'}, status=400)

        message = TicketMessage.objects.create(
            ticket=ticket,
            user=profile,
            body=body,
        )

        if is_curator:
            ticket.is_open = False
            ticket.save(update_fields=['is_open'])

        return JsonResponse({
            'message': {
                'id': message.id,
                'body': message.body,
                'time': message.time.isoformat(),
                'author': profile.user.username,
            },
            'ticket_closed': not ticket.is_open,
        }, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class APIProblemBroadcast(View):
    def post(self, request, problem_code, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        try:
            problem = Problem.objects.get(code=problem_code)
        except Problem.DoesNotExist:
            return JsonResponse({'error': f'No such problem {problem_code}'}, status=404)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        username = data.get('username')
        body = data.get('body')
        contest_key = data.get('contest_key')

        if not username or not body or not contest_key:
            return JsonResponse({'error': 'username, body, contest_key required'}, status=400)

        try:
            profile = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            return JsonResponse({'error': f'No such user {username}'}, status=404)

        try:
            contest = Contest.objects.get(key=contest_key)
        except Contest.DoesNotExist:
            return JsonResponse({'error': f'No such contest {contest_key}'}, status=404)

        is_curator = (
            contest.authors.filter(id=profile.id).exists()
            or contest.curators.filter(id=profile.id).exists()
            or contest.testers.filter(id=profile.id).exists()
        )

        if not is_curator:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        problem_ct = ContentType.objects.get_for_model(Problem)
        open_tickets = Ticket.objects.filter(
            content_type=problem_ct,
            object_id=problem.id,
            is_open=True,
        )

        created = []
        for t in open_tickets:
            msg = TicketMessage.objects.create(ticket=t, user=profile, body=body)
            t.is_open = False
            t.save(update_fields=['is_open'])
            created.append({'ticket_id': t.id, 'message_id': msg.id})

        return JsonResponse({
            'broadcasted_to': len(created),
            'created': created,
        }, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class APIStandings(View):
    def get(self, request, *args, **kwargs):
        token = get_cpfed_token(request)
        if not token or token != settings.CPFED_TOKEN:
            return JsonResponse({'error': 'Unauthorized access'}, status=401)

        contest_key = request.GET.get('contest_key')
        username = request.GET.get('username')
        if not contest_key:
            return JsonResponse({'error': 'contest_key is required'}, status=400)

        try:
            payload = compute_standings(contest_key, username=username)
        except Contest.DoesNotExist:
            return JsonResponse({'error': f'No such contest with {contest_key}'}, status=404)
        except Profile.DoesNotExist:
            return JsonResponse({'error': f'No such user {username}'}, status=404)

        return JsonResponse(payload, status=200)


def attach_proctoring_token(user, contest):
    response = requests.post(
        'https://api.trustexam.ai/api/external-session/assignment.json',
        params={
            'api_token': settings.TRUSTEXAM_API_KEY
        },
        headers={
            'Content-Type': 'application/json'
        },
        json={
            "assignment": {
                "external_id": contest.key,
                "name": contest.name,
                "external_url": "https://esep.cpfed.kz",
                "settings": {
                    "proctoring_settings": {
                      "check_env": True,
                      "browser_type": "*",
                      "object_detect": False,
                      "displays_check": False,
                      "focus_detector": False,
                      "noise_detector": False,
                      "read_clipboard": 0,
                      "content_protect": False,
                      "face_landmarker": False,
                      "fullscreen_mode": False,
                      "id_verification": False,
                      "speech_detector": False,
                      "main_camera_record": False,
                      "main_camera_upload": False,
                      "photo_head_identity": 0,
                      "screen_share_record": True,
                      "screen_share_upload": False,
                      "video_head_identity": False,
                      "head_tracking_client": 0,
                      "second_camera_record": False,
                      "second_camera_upload": False,

                      "main_camera_blackhole": False,
                      "screen_share_blackhole": False,
                      "second_camera_blackhole": False,

                      "second_microphone_record": False,
                      "second_microphone_upload": False,

                      "second_microphone_blackhole": False,
                      "head_tracking_server_realtime": False,
                      "head_compare_euclidean_distance": 0.5
                    }
                }
            },
            "student": {
                "external_id": str(user.id),
                "name": user.username,
                "firstname": user.username
            }
        }
    )

    if response.status_code == 200:
        res = response.json()
        access_token = res['external_session']['token']
        token_key = f'proctoring:session:{user.id}:{contest.id}'
        cache_timeout = contest.contest_window_length.seconds
        cache.set(token_key, access_token, timeout=cache_timeout)
        return JsonResponse({'token': res['access_token']}, status=200)
    else:
        return JsonResponse({'error': 'Failed to initialize proctoring'}, status=500)