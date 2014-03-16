import pytz
from django.utils import timezone
from judge.models import Profile


class TimezoneMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated():
            # Have to do this. We drop our tables a lot in development.
            tzname = Profile.objects.get_or_create(user=request.user)[0].timezone
        else:
            tzname = 'UTC'
        timezone.activate(pytz.timezone(tzname))

    def process_response(self, request, response):
        timezone.deactivate()
        return response
