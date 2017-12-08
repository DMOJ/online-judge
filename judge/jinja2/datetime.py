import functools
from django.template.defaultfilters import date, time
from django.templatetags.tz import localtime

from . import registry


def localtime_wrapper(func):
    @functools.wraps(func)
    def wrapper(datetime, *args, **kwargs):
        if getattr(datetime, 'convert_to_local_time', True):
            datetime = localtime(datetime)
        return func(datetime, *args, **kwargs)

    return wrapper


registry.filter(localtime_wrapper(date))
registry.filter(localtime_wrapper(time))
