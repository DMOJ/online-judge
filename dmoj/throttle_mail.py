import traceback
from django.utils.log import AdminEmailHandler
from django.core.cache import cache


def new_email():
    cache.add('error_email_throttle', 0, 60)
    return cache.incr('error_email_throttle')


class ThrottledEmailHandler(AdminEmailHandler):
    def emit(self, record):
        try:
            count = new_email()
        except Exception:
            traceback.print_exc()
            pass
        else:
            if count >= 10:
                return
        AdminEmailHandler.emit(self, record)
