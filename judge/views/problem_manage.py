from django.http import Http404
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.generic import DetailView
from django.views.generic.detail import BaseDetailView

from judge.tasks import rejudge_problem_all
from judge.utils.celery import redirect_to_task_status
from judge.utils.views import TitleMixin
from judge.views.problem import ProblemMixin


class ManageProblemSubmissionMixin(ProblemMixin):
    def get_object(self, queryset=None):
        problem = super().get_object(queryset)
        user = self.request.user
        if not problem.is_subs_manageable_by(user):
            raise Http404()
        return problem


class ManageProblemSubmissionActionMixin(ManageProblemSubmissionMixin):
    def perform_action(self):
        raise NotImplementedError()

    def get(self, request, *args, **kwargs):
        raise Http404()

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            return self.no_such_problem()
        else:
            return self.perform_action()


class ManageProblemSubmissionView(TitleMixin, ManageProblemSubmissionMixin, DetailView):
    template_name = 'problem/manage_submission.html'

    def get_title(self):
        return _('Managing submissions for %s') % (self.object.name,)

    def get_content_title(self):
        return mark_safe(escape(_('Managing submissions for %s')) % (
            format_html('<a href="{1}">{0}</a>', self.object.name,
                        reverse('problem_detail', args=[self.object.code]))),)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submission_count'] = self.object.submission_set.count()
        return context


class RejudgeAllSubmissionsView(ManageProblemSubmissionActionMixin, BaseDetailView):
    def perform_action(self):
        status = rejudge_problem_all.delay(self.object.id)
        return redirect_to_task_status(status, _('Rejudging all submissions for %s...') % (self.object.name,))
