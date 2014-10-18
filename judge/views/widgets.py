from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseForbidden, Http404, HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from judge.models import Submission


__all__ = ['rejudge_submission']

@login_required
def rejudge_submission(request):
    if request.method != 'POST' or not request.user.has_perm('judge.rejudge_submission'):
        return HttpResponseForbidden()

    if 'id' not in request.POST or not request.POST['id'].isdigit():
        return HttpResponseBadRequest()

    try:
        Submission.objects.get(id=request.POST['id']).judge()
    except Submission.DoesNotExist:
        return HttpResponseBadRequest()

    return HttpResponse('success', mimetype='text/plain')
