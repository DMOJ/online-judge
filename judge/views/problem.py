from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.forms import ProblemSubmitForm
from judge.models import Problem, Profile, Submission


def get_result_table(code):
    results = {}
    submissions = Submission.objects.filter(problem__code=code) if code is not None else Submission.objects
    for code in ['AC', 'WA', 'TLE', 'IR', 'MLE']:
        results[code] = submissions.filter(result=code).count()
    results['CE'] = submissions.filter(status='CE').count()
    return [(('Accepted', 'AC'), results['AC']),
            (('Wrong Answer', 'WA'), results['WA']),
            (('Compile Error', 'CE'), results['CE']),
            (('Time Limit Exceed', 'TLE'), results['TLE']),
            (('Memory Limit Exceed', 'MLE'), results['MLE']),
            (('Invalid Return', 'IR'), results['IR']),
            (('Total', 'TOT'), sum(results.values()))]


def problem(request, code):
    try:
        problem = Problem.objects.get(code=code)
        return render_to_response('problem.html', {'problem': problem, 'results': get_result_table(code),
                                                   'title': 'Problem %s' % problem.name},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        raise Http404()


def problems(request):
    return render_to_response('problems.html', {'problems': Problem.objects.all(), 'title': 'Problems'},
                              context_instance=RequestContext(request))


@login_required
def problem_submit(request, problem=None, submission=None):
    if request.method == 'POST':
        form = ProblemSubmitForm(request.POST, instance=Submission(user=request.user.profile))
        if form.is_valid():
            if (request.user.has_perm('judge.spam_submission') and
                Submission.objects.filter(user=request.user.profile).exclude(status__in=['D', 'IE', 'CE']).count() > 2):
                    return HttpResponse('<h1>You submitted too many submissions.</h1>', status=503)
            model = form.save()
            model.judge()
            return HttpResponseRedirect(reverse('judge.views.submission_status', args=[str(model.id)]))
    else:
        initial = {'language': request.user.profile.language}
        if problem is not None:
            try:
                initial['problem'] = Problem.objects.get(code=problem)
            except ObjectDoesNotExist:
                raise Http404()
        if submission is not None:
            try:
                initial['source'] = Submission.objects.get(id=int(submission)).source
            except (ObjectDoesNotExist, ValueError):
                raise Http404()
        form = ProblemSubmitForm(initial=initial)
    return render_to_response('problem_submit.html', {'form': form, 'title': 'Submit'},
                              context_instance=RequestContext(request))