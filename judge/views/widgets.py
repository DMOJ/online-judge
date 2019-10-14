import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect
from django.utils.translation import gettext as _
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
            not submission.problem.is_editor(request.profile):
        return HttpResponseForbidden()

    submission.judge(rejudge=True)

    redirect = request.POST.get('path', None)

    return HttpResponseRedirect(redirect) if redirect else HttpResponse('success', content_type='text/plain')


class DetectTimezone(View):
    def askgeo(self, lat, long):
        if not hasattr(settings, 'ASKGEO_ACCOUNT_ID') or not hasattr(settings, 'ASKGEO_ACCOUNT_API_KEY'):
            raise ImproperlyConfigured()
        data = requests.get('http://api.askgeo.com/v1/%s/%s/query.json?databases=TimeZone&points=%f,%f' %
                            (settings.ASKGEO_ACCOUNT_ID, settings.ASKGEO_ACCOUNT_API_KEY, lat, long)).json()
        try:
            return HttpResponse(data['data'][0]['TimeZone']['TimeZoneId'], content_type='text/plain')
        except (IndexError, KeyError):
            return HttpResponse(_('Invalid upstream data: %s') % data, content_type='text/plain', status=500)

    def geonames(self, lat, long):
        if not hasattr(settings, 'GEONAMES_USERNAME'):
            raise ImproperlyConfigured()
        data = requests.get('http://api.geonames.org/timezoneJSON?lat=%f&lng=%f&username=%s' %
                            (lat, long, settings.GEONAMES_USERNAME)).json()
        try:
            return HttpResponse(data['timezoneId'], content_type='text/plain')
        except KeyError:
            return HttpResponse(_('Invalid upstream data: %s') % data, content_type='text/plain', status=500)

    def default(self, lat, long):
        raise Http404()

    def get(self, request, *args, **kwargs):
        backend = settings.TIMEZONE_DETECT_BACKEND
        try:
            lat, long = float(request.GET['lat']), float(request.GET['long'])
        except (ValueError, KeyError):
            return HttpResponse(_('Bad latitude or longitude'), content_type='text/plain', status=404)
        return {
            'askgeo': self.askgeo,
            'geonames': self.geonames,
        }.get(backend, self.default)(lat, long)
