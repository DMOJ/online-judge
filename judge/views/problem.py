from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.forms import ProblemSubmitForm
from judge.models import Problem, Profile, Submission


def get_result_table(code):
    results = {}
    for submission in Submission.objects.filter(problem__code=code) if code else Submission.objects.all():
        r = None
        if submission.result and submission.result not in ["IE"]:
            r = submission.result
            results[r] = results.get(r, 0) + 1
    return results


def problem(request, code):
    try:
        problem = Problem.objects.get(code=code)
        return render_to_response('problem.html', {'problem': problem, 'results': get_result_table(code),
                                                   'title': 'Problem %s' % problem.name},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return Http404()


def problems(request):
    return render_to_response('problems.html', {'problems': Problem.objects.all(), 'title': 'Problems'},
                              context_instance=RequestContext(request))


@login_required
def problem_submit(request, problem=None):
    if request.method == 'POST':
        form = ProblemSubmitForm(request.POST, instance=Submission(user=request.user.profile))
        if form.is_valid():
            model = form.save()
            model.judge()
            return HttpResponseRedirect(reverse('judge.view.submission_status', args=[model.id]))
    else:
        initial = {'language': request.user.profile.language}
        if problem is not None:
            try:
                initial['problem'] = Problem.objects.get(code=problem)
            except ObjectDoesNotExist:
                return Http404()
        form = ProblemSubmitForm(initial=initial)
    return render_to_response('problem_submit.html', {'form': form, 'title': 'Submit'},
                              context_instance=RequestContext(request))