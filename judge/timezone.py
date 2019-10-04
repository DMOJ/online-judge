import pytz
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.utils.timezone import make_aware


class TimezoneMiddleware(object):
    def __init__(self, get_response=None):
        self.get_response = get_response

    def get_timezone(self, request):
        tzname = settings.DEFAULT_USER_TIME_ZONE
        if request.profile:
            tzname = request.profile.timezone
        return pytz.timezone(tzname)

    def __call__(self, request):
        with timezone.override(self.get_timezone(request)):
            return self.get_response(request)


def from_database_time(datetime):
    tz = connection.timezone
    if tz is None:
        return datetime
    return make_aware(datetime, tz)
