import traceback

from django.core.cache import cache
from django.utils.log import AdminEmailHandler
from django.conf import settings

DEFAULT_THROTTLE = (10, 60)

def new_email():
    cache.add('error_email_throttle', 0, getattr(settings, 'EMAIL_THROTTLING', DEFAULT_THROTTLE)[1])
    return cache.incr('error_email_throttle')


class ThrottledEmailHandler(AdminEmailHandler):
    def __init__(self, *args, **kwargs):
        super(ThrottledEmailHandler, self).__init__(*args, **kwargs)

        self.throttle = getattr(settings, 'EMAIL_THROTTLING', DEFAULT_THROTTLE)[0]

    def emit(self, record):
        try:
            count = new_email()
        except Exception:
            traceback.print_exc()
            pass
        else:
            if count >= self.throttle:
                return
        AdminEmailHandler.emit(self, record)
