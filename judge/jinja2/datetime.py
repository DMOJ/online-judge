import functools

from django.template.defaultfilters import date, time
from django.templatetags.tz import localtime
from django.utils.translation import gettext as _

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


@registry.function
@registry.render_with('widgets/relative-time.html')
def relative_time(time, **kwargs):
    return {
        'time': time,
        'format': kwargs.get('format', _('N j, Y, g:i a')),
        'rel_format': kwargs.get('rel', _('{time}')),
        'abs_format': kwargs.get('abs', _('on {time}')),
    }
