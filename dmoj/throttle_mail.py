import traceback

from django.core.cache import cache
from django.utils.log import AdminEmailHandler


def new_email():
    cache.add('error_email_throttle', 0, 60)
    return cache.incr('error_email_throttle')


class ThrottledEmailHandler(AdminEmailHandler):
    def __init__(self, *args, **kwargs):
        super(ThrottledEmailHandler, self).__init__(*args, **kwargs)

        from django.conf import settings
        self.throttle = getattr(settings, 'EMAIL_THROTTLING', 10)

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
