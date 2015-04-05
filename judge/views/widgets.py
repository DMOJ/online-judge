from contextlib import closing
import json
import urllib2

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseBadRequest, HttpResponse, Http404
from django.views.generic import View

from judge.models import Submission


__all__ = ['rejudge_submission', 'DetectTimezone']

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
    return HttpResponse('success', content_type='text/plain')


class DetectTimezone(View):
    def get(self, request, *args, **kwargs):
        if not hasattr(settings, 'ASKGEO_ACCOUNT_ID') or not hasattr(settings, 'ASKGEO_ACCOUNT_API_KEY'):
            raise Http404()
        try:
            lat, long = float(request.GET['lat']), float(request.GET['long'])
        except (ValueError, KeyError):
            return HttpResponse('Bad latitude or longitude', content_type='text/plain', status=404)
        with closing(urllib2.urlopen('http://api.askgeo.com/v1/%s/%s/query.json?databases=TimeZone&points=%f,%f' %
                     (settings.ASKGEO_ACCOUNT_ID, settings.ASKGEO_ACCOUNT_API_KEY, lat, long))) as f:
            data = json.load(f)
            try:
                return HttpResponse(data['data'][0]['TimeZone']['TimeZoneId'], content_type='text/plain')
            except (IndexError, KeyError):
                return HttpResponse('Invalid upstream data: %s' % data, content_type='text/plain', status=500)
