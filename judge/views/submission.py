from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db.models import F
from django.http import Http404, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.translation import ugettext as _, ugettext_lazy as __
from django.views.generic import ListView, DetailView

from judge import event_poster as event
from judge.highlight_code import highlight_code
from judge.models import Problem, Submission, Profile, Contest
from judge.utils.diggpaginator import DiggPaginator
from judge.utils.problems import user_completed_ids, get_result_table
from judge.utils.views import TitleMixin


def submission_related(queryset):
    return queryset.select_related('user__user', 'problem', 'language')\
                   .only('id', 'user__user__username', 'user__name', 'user__display_rank', 'problem__name',
                         'problem__code', 'language__short_name', 'language__key', 'date', 'time', 'memory',
                         'points', 'result', 'status', 'case_points', 'case_total', 'current_testcase')


class SubmissionMixin(object):
    model = Submission
    context_object_name = 'submission'
    pk_url_kwarg = 'submission'


class SubmissionDetailBase(LoginRequiredMixin, TitleMixin, SubmissionMixin, DetailView):
    def get_object(self, queryset=None):
        submission = super(SubmissionDetailBase, self).get_object(queryset)
        profile = self.request.user.profile

        if not self.request.user.has_perm('judge.view_all_submission') and submission.user_id != profile.id and \
                not submission.problem.authors.filter(id=profile.id).exists() and \
                not (submission.problem.is_public and
                     Submission.objects.filter(user_id=profile.id, result='AC',
                                               problem__code=submission.problem.code,
                                               points=F('problem__points')).exists()):
            raise PermissionDenied()
        return submission

    def get_title(self):
        submission = self.object
        return _('Submission of %s by %s') % (submission.problem.name, submission.user.user.username)


class SubmissionSource(SubmissionDetailBase):
    template_name = 'submission/source.jade'

    def get_context_data(self, **kwargs):
        context = super(SubmissionSource, self).get_context_data(**kwargs)
        submission = self.object
        context['raw_source'] = submission.source.rstrip('\n')
        context['highlighted_source'] = highlight_code(submission.source, submission.language.pygments)
        return context


class SubmissionStatus(SubmissionDetailBase):
    template_name = 'submission/status.jade'

    def get_context_data(self, **kwargs):
        context = super(SubmissionStatus, self).get_context_data(**kwargs)
        submission = self.object
        context['last_msg'] = event.last()
        context['test_cases'] = submission.test_cases.all()
        context['time_limit'] = submission.problem.time_limit
        try:
            lang_limit = submission.problem.language_limits.get(language=submission.language)
        except ObjectDoesNotExist:
            pass
        else:
            context['time_limit'] = lang_limit.time_limit
        return context


class SubmissionTestCaseQuery(SubmissionStatus):
    template_name = 'submission/status_testcases.jade'

    def get(self, request, *args, **kwargs):
        if 'id' not in request.GET or not request.GET['id'].isdigit():
            return HttpResponseBadRequest()
        self.kwargs[self.pk_url_kwarg] = kwargs[self.pk_url_kwarg] = int(request.GET['id'])
        return super(SubmissionTestCaseQuery, self).get(request, *args, **kwargs)


def abort_submission(request, submission):
    if request.method != 'POST':
        raise Http404()
    submission = get_object_or_404(Submission, id=int(submission))
    if not request.user.is_authenticated() or \
            request.user.profile != submission.user and not request.user.has_perm('abort_any_submission'):
        raise PermissionDenied()
    submission.abort()
    return HttpResponseRedirect(reverse('submission_status', args=(submission.id,)))


class SubmissionsListBase(TitleMixin, ListView):
    model = Submission
    paginate_by = 50
    show_problem = True
    title = __('All submissions')
    template_name = 'submission/list.jade'
    context_object_name = 'submissions'
    first_page_href = None

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        return DiggPaginator(queryset, per_page, body=6, padding=2,
                             orphans=orphans, allow_empty_first_page=allow_empty_first_page, **kwargs)

    def get_result_table(self):
        return get_result_table(self.get_queryset().order_by())

    def access_check(self, request):
        pass

    @cached_property
    def in_contest(self):
        return self.request.user.is_authenticated() and self.request.user.profile.contest.current is not None

    @cached_property
    def contest(self):
        return self.request.user.profile.contest.current.contest

    def _get_queryset(self):
        queryset = submission_related(Submission.objects.order_by('-id'))
        if self.in_contest:
            return queryset.filter(contest__participation__contest_id=self.contest.id)
        return queryset

    def get_queryset(self):
        queryset = self._get_queryset()
        if not self.in_contest and not self.request.user.has_perm('judge.see_private_problem'):
            queryset = queryset.filter(problem__is_public=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(SubmissionsListBase, self).get_context_data(**kwargs)
        context['dynamic_update'] = False
        context['show_problem'] = self.show_problem
        context['completed_problem_ids'] = (user_completed_ids(self.request.user.profile)
                                            if self.request.user.is_authenticated() else [])
        context['results'] = self.get_result_table()
        context['first_page_href'] = self.first_page_href or '.'
        return context

    def get(self, request, *args, **kwargs):
        check = self.access_check(request)
        if check is not None:
            return check
        if 'results' in request.GET:
            return render(request, 'problem/statistics_table.jade', {'results': self.get_result_table()})
        return super(SubmissionsListBase, self).get(request, *args, **kwargs)


class UserMixin(object):
    def get(self, request, *args, **kwargs):
        if 'user' not in kwargs:
            raise ImproperlyConfigured('Must pass a user')
        try:
            self.profile = Profile.objects.get(user__username=kwargs['user'])
        except Profile.DoesNotExist:
            raise Http404()
        else:
            self.username = kwargs['user']
        return super(UserMixin, self).get(request, *args, **kwargs)


class AllUserSubmissions(UserMixin, SubmissionsListBase):
    def get_queryset(self):
        return super(AllUserSubmissions, self).get_queryset().filter(user_id=self.profile.id)

    def get_title(self):
        return _('All submissions by %s') % self.username

    def get_content_title(self):
        return format_html(u'All submissions by <a href="{1}">{0}</a>', self.username,
                           reverse('user_page', args=[self.username]))

    def get_context_data(self, **kwargs):
        context = super(AllUserSubmissions, self).get_context_data(**kwargs)
        context['dynamic_update'] = context['page_obj'].number == 1
        context['dynamic_user_id'] = self.profile.id
        context['last_msg'] = event.last()
        return context


class ProblemSubmissions(SubmissionsListBase):
    show_problem = False
    dynamic_update = True

    def get_queryset(self):
        return super(ProblemSubmissions, self)._get_queryset().filter(problem__code=self.problem.code)

    def get_title(self):
        return _('All submissions for %s') % self.problem.name

    def get_content_title(self):
        return format_html(u'All submissions for <a href="{1}">{0}</a>', self.problem.name,
                           reverse('problem_detail', args=[self.problem.code]))

    def access_check(self, request):
        if not self.problem.is_public:
            user = request.user
            if not user.is_authenticated():
                raise Http404()

            if not self.problem.authors.filter(id=user.profile.id).exists() and \
                    not user.has_perm('judge.see_private_problem') and \
                    not (self.in_contest and self.contest.problems.filter(id=self.problem.id).exists()):
                raise Http404()

    def get(self, request, *args, **kwargs):
        if 'problem' not in kwargs:
            raise ImproperlyConfigured(_('Must pass a problem'))
        try:
            self.problem = Problem.objects.get(code=kwargs['problem'])
        except Problem.DoesNotExist:
            raise Http404()
        return super(ProblemSubmissions, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProblemSubmissions, self).get_context_data(**kwargs)
        if self.dynamic_update:
            context['dynamic_update'] = context['page_obj'].number == 1
            context['dynamic_problem_id'] = self.problem.id
            context['last_msg'] = event.last()
        return context


class UserProblemSubmissions(UserMixin, ProblemSubmissions):
    def get_queryset(self):
        return super(UserProblemSubmissions, self).get_queryset().filter(user_id=self.profile.id)

    def get_title(self):
        return _("%s's submissions for %s") % (self.username, self.problem.name)

    def get_content_title(self):
        return format_html(u'''<a href="{1}">{0}</a>'s submissions for <a href="{3}">{2}</a>''',
                           self.username, reverse('user_page', args=[self.username]),
                           self.problem.name, reverse('problem_detail', args=[self.problem.code]))

    def get_context_data(self, **kwargs):
        context = super(UserProblemSubmissions, self).get_context_data(**kwargs)
        context['dynamic_user_id'] = self.profile.id
        return context


def single_submission(request, submission, show_problem=True):
    try:
        authenticated = request.user.is_authenticated()
        return render(request, 'submission/row.jade', {
            'submission': get_object_or_404(submission_related(Submission.objects.all()), id=int(submission)),
            'completed_problem_ids': user_completed_ids(request.user.profile) if authenticated else [],
            'show_problem': show_problem,
            'profile_id': request.user.profile.id if authenticated else 0,
        })
    except ObjectDoesNotExist:
        raise Http404()


def single_submission_query(request):
    if 'id' not in request.GET or not request.GET['id'].isdigit():
        return HttpResponseBadRequest()
    try:
        show_problem = int(request.GET.get('show_problem', '1'))
    except ValueError:
        return HttpResponseBadRequest()
    return single_submission(request, int(request.GET['id']), show_problem)


class AllSubmissions(SubmissionsListBase):
    def get_context_data(self, **kwargs):
        context = super(AllSubmissions, self).get_context_data(**kwargs)
        context['dynamic_update'] = context['page_obj'].number == 1
        context['last_msg'] = event.last()
        return context


class ForceContestMixin(object):
    @property
    def in_contest(self):
        return True

    @property
    def contest(self):
        return self._contest

    def access_check(self, request):
        if not request.user.has_perm('judge.see_private_contest'):
            if not self.contest.is_public:
                raise Http404()
            if self.contest.start_time is not None and self.contest.start_time > timezone.now():
                raise Http404()

    def get(self, request, *args, **kwargs):
        if 'contest' not in kwargs:
            raise ImproperlyConfigured(_('Must pass a contest'))
        try:
            self._contest = Contest.objects.get(key=kwargs['contest'])
        except Contest.DoesNotExist:
            raise Http404()
        return super(ForceContestMixin, self).get(request, *args, **kwargs)


class UserContestSubmissions(ForceContestMixin, UserProblemSubmissions):
    def get_title(self):
        return "%s's submissions for %s in %s" % (self.username, self.problem.name, self.contest.name)

    def get_content_title(self):
        return format_html(_(u'<a href="{1}">{0}</a>\'s submissions for '
                             u'<a href="{3}">{2}</a> in <a href="{5}">{4}</a>'),
                           self.username, reverse('user_page', args=[self.username]),
                           self.problem.name, reverse('problem_detail', args=[self.problem.code]),
                           self.contest.name, reverse('contest_view', args=[self.contest.key]))
