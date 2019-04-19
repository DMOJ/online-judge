import pytz
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db import connection
from django.utils.timezone import make_aware

from judge.models import Profile


class TimezoneMiddleware(object):
    def __init__(self, get_response=None):
        self.get_response = get_response

    def process_request(self, request):
        timezone.activate(self.get_timezone(request))

    def get_timezone(self, request):
        if request.user.is_authenticated:
            try:
                tzname = Profile.objects.get(user=request.user).timezone
            except ObjectDoesNotExist:
                tzname = getattr(settings, 'DEFAULT_USER_TIME_ZONE', 'America/Toronto')
        else:
            tzname = getattr(settings, 'DEFAULT_USER_TIME_ZONE', 'America/Toronto')
        return pytz.timezone(tzname)

    def process_response(self, request, response):
        timezone.deactivate()
        return response

    def __call__(self, request):
        with timezone.override(self.get_timezone(request)):
            return self.get_response(request)


def from_database_time(datetime):
    tz = connection.timezone
    if tz is None:
        return datetime
    return make_aware(datetime, tz)
