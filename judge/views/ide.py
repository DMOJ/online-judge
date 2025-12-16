from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from judge.models import Language, Problem, Submission, SubmissionSource
from judge.utils.views import TitleMixin

__all__ = ['IDEView', 'IDESubmitView', 'IDESubmissionStatus']

# IDE configuration constants
MINUTES_TO_SECONDS = 60
IDE_PROBLEM_CODE = 'idepractice'

# Rate limiting configuration
IDE_RATE_LIMIT_COUNT = 5  # runs per window
IDE_RATE_LIMIT_WINDOW = 1  # minutes

# Resource limits for IDE (lower than problem limits)
IDE_TIME_LIMIT = 2.0  # seconds
IDE_MEMORY_LIMIT = 65536  # KB (64 MB)
IDE_OUTPUT_LIMIT = 10240  # bytes (10 KB)


class IDEView(LoginRequiredMixin, TitleMixin, TemplateView):
    """
    Main IDE page with code editor, input editor, and output display.
    """
    template_name = 'ide/ide.html'
    title = 'IDE'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['languages'] = Language.objects.filter(
            judges__online=True,
        ).distinct().order_by('name', 'key')
        context['ACE_URL'] = settings.ACE_URL
        context['default_lang'] = self.request.profile.language
        context['ace_theme'] = self.request.profile.resolved_ace_theme
        context['rate_limit_count'] = IDE_RATE_LIMIT_COUNT
        context['rate_limit_window'] = IDE_RATE_LIMIT_WINDOW
        return context


class IDESubmitView(LoginRequiredMixin, View):
    """
    AJAX endpoint to submit IDE code for execution.
    """

    def post(self, request):
        # Rate limiting check
        cache_key = f'ide_run:{request.profile.id}'
        current_count = cache.get(cache_key, 0)

        if current_count >= IDE_RATE_LIMIT_COUNT:
            return JsonResponse({
                'error':
                f'Rate limit exceeded. Maximum {IDE_RATE_LIMIT_COUNT} runs per {IDE_RATE_LIMIT_WINDOW} minute(s).',
            }, status=429)

        # Parse request
        source_code = request.POST.get('source', '')
        language_id = request.POST.get('language')
        custom_input = request.POST.get('input', '')

        # Validation
        if not source_code or len(source_code) > 65536:
            return JsonResponse({
                'error': 'Source code must be between 1 and 65536 characters.',
            }, status=400)

        if len(custom_input) > 65536:
            return JsonResponse({
                'error': 'Input must be at most 65536 characters.',
            }, status=400)

        try:
            language = Language.objects.get(id=language_id, judges__online=True)
        except Language.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid or unavailable language.',
            }, status=400)

        # Get IDE problem
        try:
            ide_problem = Problem.objects.get(code=IDE_PROBLEM_CODE)
        except Problem.DoesNotExist:
            return JsonResponse({
                'error': 'IDE feature not configured. Contact administrator.',
            }, status=500)

        # Check global submission limit (reuse existing spam check)
        if (not request.user.has_perm('judge.spam_submission') and
            Submission.objects.filter(user=request.profile, rejudged_date__isnull=True)
                              .exclude(status__in=['D', 'IE', 'CE', 'AB'])
                              .count() >= settings.DMOJ_SUBMISSION_LIMIT):
            return JsonResponse({
                'error': 'You have too many submissions in queue. Please wait.',
            }, status=429)

        # Create submission
        with transaction.atomic():
            submission = Submission(
                user=request.profile,
                problem=ide_problem,
                language=language,
            )
            submission.save()

            source = SubmissionSource(
                submission=submission,
                source=source_code,
            )
            source.save()
            submission.source = source

        # Store custom input in cache (accessible by judge callback)
        cache.set(f'ide_input:{submission.id}', custom_input, timeout=600)  # 10 minutes

        # Judge submission with custom limits
        submission.judge(force_judge=True, judge_id=None)

        # Increment rate limit counter
        if current_count == 0:
            cache.set(cache_key, 1, timeout=IDE_RATE_LIMIT_WINDOW * MINUTES_TO_SECONDS)
        else:
            cache.incr(cache_key)

        return JsonResponse({
            'success': True,
            'submission_id': submission.id,
            'submission_url': reverse('ide_submission_status', args=[submission.id]),
        })


class IDESubmissionStatus(LoginRequiredMixin, View):
    """
    AJAX endpoint to check submission status and retrieve output.
    Returns submission progress and truncated output.
    """

    def get(self, request, submission):
        submission_obj = get_object_or_404(Submission, id=submission)

        # Security check: only allow viewing own IDE submissions
        if submission_obj.user_id != request.profile.id:
            return JsonResponse({'error': 'Access denied.'}, status=403)

        if submission_obj.problem.code != IDE_PROBLEM_CODE:
            return JsonResponse({'error': 'Not an IDE submission.'}, status=400)

        # Build response
        response = {
            'status': submission_obj.status,
            'result': submission_obj.result,
            'error': submission_obj.error,
            'time': submission_obj.time,
            'memory': submission_obj.memory,
        }

        # Add output if graded
        if submission_obj.is_graded:
            test_cases = submission_obj.test_cases.all()
            if test_cases:
                # For IDE, there should be exactly one test case
                test_case = test_cases[0]
                output = test_case.output or ''

                # Truncate to 10KB
                if len(output) > IDE_OUTPUT_LIMIT:
                    output = output[:IDE_OUTPUT_LIMIT] + '\n\n[Output truncated to 10KB]'

                response['output'] = output
                response['test_case_status'] = test_case.status
                response['test_case_time'] = test_case.time
                response['test_case_memory'] = test_case.memory

        return JsonResponse(response)
