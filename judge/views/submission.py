from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db.models import F
from django.http import Http404, HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext, loader
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.views.generic import TemplateView, ListView
from django.views.generic.detail import SingleObjectMixin

from judge.highlight_code import highlight_code
from judge.models import Problem, Submission, SubmissionTestCase, Profile, Contest
from judge.utils.problems import user_completed_ids, get_result_table
from judge.utils.diggpaginator import DiggPaginator
from judge.utils.views import TitleMixin
from judge import event_poster as event


def submission_related(queryset):
    return queryset.select_related('user__user', 'problem', 'language')\
                   .only('id', 'user__user__username', 'user__name', 'user__display_rank', 'problem__name',
                         'problem__code', 'language__short_name', 'language__key', 'date', 'time', 'memory',
                         'points', 'result', 'status', 'case_points', 'case_total', 'current_testcase')


class SubmissionMixin(object):
    model = Submission


class SubmissionDetailBase(TitleMixin, SubmissionMixin, SingleObjectMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        self.object = submission = self.get_object()

        profile = request.user.profile
        if not request.user.has_perm('judge.view_all_submission') and submission.user_id != profile.id and \
                not submission.problem.authors.filter(id=profile.id).exists() and \
                not Submission.objects.filter(user_id=profile.id, result='AC',
                                              problem__code=submission.problem.code,
                                              points=F('problem__points')).exists():
            raise PermissionDenied()

        return super(SubmissionDetailBase, self).get(request, *args, submission=self.object, **kwargs)

    def get_title(self):
        submission = self.object
        return 'Submission of %s by %s' % (submission.problem.name, submission.user.user.username)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(SubmissionDetailBase, self).dispatch(*args, **kwargs)


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
        return context


class SubmissionTestCaseQuery(SubmissionStatus):
    template_name = 'submission/status_testcases.jade'

    def get(self, request, *args, **kwargs):
        if 'id' not in request.GET or not request.GET['id'].isdigit():
            return HttpResponseBadRequest()
        kwargs[self.pk_url_kwarg] = int(request.GET.pop('id'))
        return super(SubmissionTestCaseQuery, self).get(request, *args, **kwargs)


def abort_submission(request, code):
    if request.method != 'POST':
        raise Http404()
    submission = Submission.objects.get(id=int(code))
    if not request.user.is_authenticated() or \
            request.user.profile != submission.user and not request.user.has_perm('abort_any_submission'):
        raise PermissionDenied()
    submission.abort()
    return HttpResponseRedirect(reverse('submission_status', args=(code,)))


class SubmissionsListBase(TitleMixin, ListView):
    model = Submission
    paginate_by = 50
    show_problem = True
    title = 'All submissions'
    template_name = 'submission/list.jade'
    context_object_name = 'submissions'
    first_page_href = None

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        return DiggPaginator(queryset, per_page, body=6, padding=2,
                             orphans=orphans, allow_empty_first_page=allow_empty_first_page, **kwargs)

    def get_result_table(self):
        return get_result_table(self.get_queryset())

    def access_check(self, request):
        pass

    @cached_property
    def in_contest(self):
        return self.request.user.is_authenticated() and self.request.user.profile.contest.current is not None

    @cached_property
    def contest(self):
        return self.request.user.profile.contest.current.contest

    def get_queryset(self):
        queryset = submission_related(Submission.objects.order_by('-id'))
        if self.in_contest:
            return queryset.filter(contest__participation__contest_id=self.contest.id)
        else:
            if not self.request.user.has_perm('judge.see_private_problem'):
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
            return render_to_response('problem/statistics_table.jade', {'results': self.get_result_table()})
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
        return 'All submissions by %s' % self.username

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
        return super(ProblemSubmissions, self).get_queryset().filter(problem__code=self.problem.code)

    def get_title(self):
        return 'All submissions for %s' % self.problem.name

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
            raise ImproperlyConfigured('Must pass a problem')
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
        return "%s's submissions for %s" % (self.username, self.problem.name)

    def get_content_title(self):
        return format_html(u'''<a href="{1}">{0}</a>'s submissions for <a href="{3}">{2}</a>''',
                           self.username, reverse('user_page', args=[self.username]),
                           self.problem.name, reverse('problem_detail', args=[self.problem.code]))

    def get_context_data(self, **kwargs):
        context = super(UserProblemSubmissions, self).get_context_data(**kwargs)
        context['dynamic_user_id'] = self.profile.id
        return context


def single_submission(request, id, show_problem=True):
    try:
        authenticated = request.user.is_authenticated()
        return render_to_response('submission/row.jade', {
            'submission': submission_related(Submission.objects).get(id=int(id)),
            'completed_problem_ids': user_completed_ids(request.user.profile) if authenticated else [],
            'show_problem': show_problem,
            'profile_id': request.user.profile.id if authenticated else 0,
        }, context_instance=RequestContext(request))
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
            raise ImproperlyConfigured('Must pass a contest')
        try:
            self._contest = Contest.objects.get(key=kwargs['contest'])
        except Contest.DoesNotExist:
            raise Http404()
        return super(ForceContestMixin, self).get(request, *args, **kwargs)


class UserContestSubmissions(ForceContestMixin, UserProblemSubmissions):
    def get_title(self):
        return "%s's submissions for %s in %s" % (self.username, self.problem.name, self.contest.name)

    def get_content_title(self):
        return format_html(u'<a href="{1}">{0}</a>\'s submissions for <a href="{3}">{2}</a> in <a href="{5}">{4}</a>',
                           self.username, reverse('user_page', args=[self.username]),
                           self.problem.name, reverse('problem_detail', args=[self.problem.code]),
                           self.contest.name, reverse('contest_view', args=[self.contest.key]))
