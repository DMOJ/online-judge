from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.models import Problem, Submission
from judge.views import get_result_table


def submission_status(request, code):
    #TODO: should only show "Click here to revise and resubmit!" if user is the author of the submission
    try:
        submission = Submission.objects.get(id=int(code))
        return render_to_response('submission_status.html',
                                  {'submission': submission, 'title': 'Submission of %s by %s' %
                                                                      (submission.problem.name, submission.user.name)},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return Http404()


def problem_submissions(request, code, title, order=['-id']):
    try:
        problem = Problem.objects.get(code=code)
        submissions = Submission.objects.filter(problem=problem).order_by(*order)
        return render_to_response('problem_submissions.html',
                                  {'submissions': submissions,
                                   'results': get_result_table(code),
                                   'title': title % problem.name},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return Http404()


def submissions(request):
    return render_to_response('submissions.html',
                              {'submissions': Submission.objects.all(), 'results': get_result_table(None),
                               'title': 'All submissions'},
                              context_instance=RequestContext(request))