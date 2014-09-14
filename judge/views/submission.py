from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.models import Problem, Submission, SubmissionTestCase
from judge.utils.diggpaginator import DiggPaginator
from judge.views import get_result_table


def submission_status(request, code):
    try:
        submission = Submission.objects.get(id=int(code))
        test_cases = SubmissionTestCase.objects.filter(submission=submission)
        return render_to_response('submission_status.html',
                                  {'submission': submission, 'test_cases': test_cases,
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
            request.user.profile != submission.user and not request.user.profile.is_admin()):
        raise PermissionDenied()
    submission.abort()
    return HttpResponseRedirect(reverse('judge.views.submission_status', args=(code,)))


def user_submissions(request, code, username, page=1):
    return problem_submissions(request, code, page, False, title="All submissions for %s", order=['-id'],
                               filter={
                                   'problem__code': code,
                                   'user__username': username
                               }
    )


def chronological_submissions(request, code, page=1):
    return problem_submissions(request, code, page, False, title="All submissions for %s", order=['-id'],
                               filter={'problem__code': code})


def problem_submissions(request, code, page, dynamic_update, title, order, filter={}):
    try:
        problem = Problem.objects.get(code=code)
        submissions = Submission.objects.filter(**filter).order_by(*order)

        paginator = DiggPaginator(submissions, 50, body=6, padding=2)
        try:
            submissions = paginator.page(page)
        except PageNotAnInteger:
            submissions = paginator.page(1)
        except EmptyPage:
            submissions = paginator.page(paginator.num_pages)
        return render_to_response('submissions.html',
                                  {'submissions': submissions,
                                   'results': get_result_table(problem__code=code),
                                   'dynamic_update': dynamic_update,
                                   'title': title % problem.name,
                                   'show_problem': False},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        raise Http404()


def submissions(request, page=1):
    paginator = DiggPaginator(Submission.objects.order_by('-id'), 50, body=6, padding=2)
    try:
        submissions = paginator.page(page)
    except PageNotAnInteger:
        submissions = paginator.page(1)
    except EmptyPage:
        submissions = paginator.page(paginator.num_pages)
    return render_to_response('submissions.html',
                              {'submissions': submissions,
                               'results': get_result_table(),
                               'dynamic_update': True if page == 1 else False,
                               'title': 'All submissions',
                               'show_problem': True},
                              context_instance=RequestContext(request))