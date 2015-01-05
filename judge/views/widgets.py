from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseBadRequest, HttpResponse

from judge.models import Submission


__all__ = ['rejudge_submission']

@login_required
def rejudge_submission(request):
    if request.method != 'POST' or not request.user.has_perm('judge.rejudge_submission') or \
            not request.user.has_perm('judge.edit_own_problem'):
        return HttpResponseForbidden()

    if 'id' not in request.POST or not request.POST['id'].isdigit():
        return HttpResponseBadRequest()

    try:
        submission = Submission.objects.get(id=request.POST['id'])
    except Submission.DoesNotExist:
        return HttpResponseBadRequest()

    if not request.user.has_perm('judge.edit_all_problem') and \
            not submission.problem.authors.filter(id=request.user.profile.id).exists():
        return HttpResponseForbidden()

    submission.judge()
    return HttpResponse('success', mimetype='text/plain')
