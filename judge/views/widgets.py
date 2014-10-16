from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseForbidden, Http404, HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from judge.models import Submission

@login_required
def rejudge_submission(request):
    if request.method != 'POST':
        return HttpResponseForbidden()

    if 'id' not in request.POST:
        return HttpResponseBadRequest()

    Submission.objects.get(id=id).judge()

    return HttpResponse('success', mimetype='text/plain')
