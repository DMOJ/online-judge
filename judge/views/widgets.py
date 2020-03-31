import json
import os
import uuid
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import View
from martor.api import imgur_uploader

from judge.models import Submission

__all__ = ['rejudge_submission', 'DetectTimezone']


@login_required
@require_POST
def rejudge_submission(request):
    if 'id' not in request.POST or not request.POST['id'].isdigit():
        return HttpResponseBadRequest()

    try:
        submission = Submission.objects.get(id=request.POST['id'])
    except Submission.DoesNotExist:
        return HttpResponseBadRequest()

    if not submission.problem.is_subs_manageable_by(request.user):
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


def django_uploader(image):
    ext = os.path.splitext(image.name)[1]
    if ext not in settings.MARTOR_UPLOAD_SAFE_EXTS:
        ext = '.png'
    name = str(uuid.uuid4()) + ext
    default_storage.save(os.path.join(settings.MARTOR_UPLOAD_MEDIA_DIR, name), image)
    url_base = getattr(settings, 'MARTOR_UPLOAD_URL_PREFIX',
                       urljoin(settings.MEDIA_URL, settings.MARTOR_UPLOAD_MEDIA_DIR))
    if not url_base.endswith('/'):
        url_base += '/'
    return json.dumps({'status': 200, 'name': '', 'link': urljoin(url_base, name)})


@login_required
def martor_image_uploader(request):
    if request.method != 'POST' or not request.is_ajax() or 'markdown-image-upload' not in request.FILES:
        return HttpResponseBadRequest('Invalid request')

    image = request.FILES['markdown-image-upload']
    if request.user.is_staff:
        data = django_uploader(image)
    else:
        data = imgur_uploader(image)
    return HttpResponse(data, content_type='application/json')
