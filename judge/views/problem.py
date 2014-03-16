from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.forms import ProblemSubmitForm
from judge.models import Problem, Profile


def problem(request, code):
    try:
        problem = Problem.objects.get(code=code)
        return render_to_response('problem.html', {'problem': problem, 'title': 'Problem %s' % problem.name},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return Http404()


def problems(request):
    return render_to_response('problems.html', {'problems': Problem.objects.all(), 'title': 'Problems'},
                              context_instance=RequestContext(request))


@login_required
def problem_submit(request):
    profile = Profile.objects.get(user=request.user)
    if request.method == 'POST':
        form = ProblemSubmitForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.path)
    else:
        form = ProblemSubmitForm(instance=profile)
    return render_to_response('problem_submit.html', {'form': form, 'title': 'Submit'},
                              context_instance=RequestContext(request))