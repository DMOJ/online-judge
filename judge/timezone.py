import pytz
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from judge.models import Profile


class TimezoneMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            try:
                tzname = Profile.objects.get(user=request.user).timezone
            except ObjectDoesNotExist:
                tzname = 'America/Toronto'
        else:
            tzname = 'America/Toronto'
        timezone.activate(pytz.timezone(tzname))

    def process_response(self, request, response):
        timezone.deactivate()
        return response
