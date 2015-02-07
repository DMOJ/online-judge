import pytz
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from judge.models import Profile


class TimezoneMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            try:
                tzname = Profile.objects.get(user=request.user).timezone
            except ObjectDoesNotExist:
                tzname = getattr(settings, 'DEFAULT_USER_TIME_ZONE', 'America/Tronto')
        else:
            tzname = getattr(settings, 'DEFAULT_USER_TIME_ZONE', 'America/Tronto')
        timezone.activate(pytz.timezone(tzname))

    def process_response(self, request, response):
        timezone.deactivate()
        return response
