from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.forms import ProblemSubmitForm
from judge.models import Problem, Profile, Submission


def submission_status(request, code):
    try:
        submission = Submission.objects.get(id=int(code))
        return render_to_response('submission_status.html', {'submission': submission, 'title': 'Submission %s' % code},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return Http404()