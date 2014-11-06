from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.db.models import F
from django.http import Http404, HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext, loader

from judge.highlight_code import highlight_code
from judge.models import Problem, Submission, SubmissionTestCase, Profile
from judge.utils.diggpaginator import DiggPaginator
from judge.views import get_result_table, user_completed_ids
from judge import event_poster as event


def check_submission_access(request, submission):
    if not request.user.is_authenticated():
        raise PermissionDenied()

    if not request.user.profile.is_admin and submission.user != request.user.profile and \
            not Submission.objects.filter(user=request.user.profile, result='AC',
                                          problem__code=submission.problem.code,
                                          points=F('problem__points')).exists():
        raise PermissionDenied()


def submission_source(request, sub_id):
    try:
        submission = Submission.objects.get(id=int(sub_id))
        check_submission_access(request, submission)

        return render_to_response('submission_source.jade',
                                  {
                                      'submission': submission,
                                      'raw_source': submission.source.rstrip('\n'),
                                      'highlighted_source': highlight_code(submission.source, submission.language.pygments),
                                      'title': 'Submission of %s by %s' %
                                            (submission.problem.name, submission.user.user.username)
                                  },
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        raise Http404()


def submission_status(request, code):
    try:
        submission = Submission.objects.get(id=int(code))
        check_submission_access(request, submission)

        test_cases = SubmissionTestCase.objects.filter(submission=submission)
        return render_to_response('submission_status.jade',
                                  {'submission': submission, 'test_cases': test_cases,
                                   'last_msg': event.last(),
                                   'title': 'Submission of %s by %s' %
                                            (submission.problem.name, submission.user.user.username)},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        raise Http404()


def abort_submission(request, code):
    if request.method != 'POST':
        raise Http404()
    submission = Submission.objects.get(id=int(code))
    if not request.user.is_authenticated() or (
                    request.user.profile != submission.user and not request.user.profile.is_admin):
        raise PermissionDenied()
    submission.abort()
    return HttpResponseRedirect(reverse('judge.views.submission_status', args=(code,)))


def all_user_submissions(request, username, page=1):
    queryset = Submission.objects.filter(user__user__username=username).order_by('-id')
    if request.user.is_authenticated() and request.user.profile.contest.current is not None:
        queryset = queryset.filter(contest__participation__contest_id=request.user.profile.contest.current.contest_id)
    paginator = DiggPaginator(queryset, 50, body=6, padding=2)
    try:
        submissions = paginator.page(page)
    except PageNotAnInteger:
        submissions = paginator.page(1)
    except EmptyPage:
        submissions = paginator.page(paginator.num_pages)
    return render_to_response('submissions.jade',
                              {'submissions': submissions,
                               'results': get_result_table(user__user__username=username),
                               'dynamic_update': False,
                               'title': 'All submissions by ' + username,
                               'completed_problem_ids': user_completed_ids(
                                   request.user.profile) if request.user.is_authenticated() else [],
                               'show_problem': True},
                              context_instance=RequestContext(request))


def user_submissions(request, code, username, page=1):
    if not Profile.objects.filter(user__username=username).exists():
        raise Http404()
    return problem_submissions(request, code, page, False, title=username + "'s submissions for %s", order=['-id'],
                               filter={
                                   'problem__code': code,
                                   'user__user__username': username
                               }
    )


def chronological_submissions(request, code, page=1):
    return problem_submissions(request, code, page, False, title="All submissions for %s", order=['-id'],
                               filter={'problem__code': code})


def problem_submissions(request, code, page, dynamic_update, title, order, filter={}):
    try:
        problem = Problem.objects.get(code=code)
        queryset = Submission.objects.filter(**filter).order_by(*order)
        user = request.user
        if user.is_authenticated() and user.profile.contest.current is not None:
            queryset = queryset.filter(contest__participation__contest_id=user.profile.contest.current.contest_id)

        paginator = DiggPaginator(queryset, 50, body=6, padding=2)
        try:
            submissions = paginator.page(page)
        except PageNotAnInteger:
            submissions = paginator.page(1)
        except EmptyPage:
            submissions = paginator.page(paginator.num_pages)
        return render_to_response('submissions.jade',
                                  {'submissions': submissions,
                                   'results': get_result_table(**filter),
                                   'dynamic_update': dynamic_update,
                                   'title': title % problem.name,
                                   'completed_problem_ids': user_completed_ids(
                                       user.profile) if user.is_authenticated() else [],
                                   'show_problem': False},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        raise Http404()


def single_submission(request, id):
    try:
        authenticated = request.user.is_authenticated()
        return render_to_response('submission_row.jade', {
            'submission': Submission.objects.get(id=int(id)),
            'completed_problem_ids': user_completed_ids(request.user.profile) if authenticated else [],
            'show_problem': True,
            'profile_id': request.user.profile.id if authenticated else 0,
        }, context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        raise Http404()


def submission_testcases_query(request):
    if 'id' not in request.GET or not request.GET['id'].isdigit():
        return HttpResponseBadRequest()
    try:
        submission = Submission.objects.get(id=int(request.GET['id']))
        test_cases = SubmissionTestCase.objects.filter(submission=submission)
        return render_to_response('submission_status_testcases.jade', {
            'submission': submission, 'test_cases': test_cases
        }, context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        raise Http404()


def statistics_table_query(request):
    page = cache.get('sub_stats_table')
    if page is None:
        page = loader.render_to_string('problem_statistics_table.jade', {'results': get_result_table()})
        cache.set('sub_stats_table', page, 86400)
    return HttpResponse(page)


def single_submission_query(request):
    if 'id' not in request.GET or not request.GET['id'].isdigit():
        return HttpResponseBadRequest()
    return single_submission(request, int(request.GET['id']))


def submissions(request, page=1):
    queryset = Submission.objects.order_by('-id')
    if request.user.is_authenticated() and request.user.profile.contest.current is not None:
        queryset = queryset.filter(contest__participation__contest_id=request.user.profile.contest.current.contest_id)
    paginator = DiggPaginator(queryset, 50, body=6, padding=2)
    try:
        submissions = paginator.page(page)
    except PageNotAnInteger:
        submissions = paginator.page(1)
    except EmptyPage:
        submissions = paginator.page(paginator.num_pages)
    results = cache.get('sub_stats_data')
    if results is None:
        results = get_result_table()
        cache.set('sub_stats_data', results, 86400)
    return render_to_response('submissions.jade',
                              {'submissions': submissions,
                               'results': results,
                               'dynamic_update': True if page == 1 else False,
                               'last_msg': event.last(),
                               'title': 'All submissions',
                               'completed_problem_ids': user_completed_ids(
                                   request.user.profile) if request.user.is_authenticated() else [],
                               'show_problem': True},
                              context_instance=RequestContext(request))
