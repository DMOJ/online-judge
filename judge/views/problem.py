from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.models import Problem


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
