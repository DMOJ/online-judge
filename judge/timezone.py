import pytz
from django.utils import timezone
from judge.models import Profile


class TimezoneMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            tzname = Profile.objects.get(user=request.user).timezone
        else:
            tzname = 'UTC'
        timezone.activate(pytz.timezone(tzname))

    def process_response(self, request, response):
        timezone.deactivate()
        return response
