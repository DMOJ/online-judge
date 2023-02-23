import functools

from django.template.defaultfilters import date, time
from django.templatetags.tz import localtime
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.timezone import utc
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
def relative_time(time, **kwargs):
    abs_time = date(time, kwargs.get('format', _('N j, Y, g:i a')))
    return mark_safe(f'<span data-iso="{time.astimezone(utc).isoformat()}" class="time-with-rel"'
                     f' title="{escape(abs_time)}" data-format="{escape(kwargs.get("rel", _("{time}")))}">'
                     f'{escape(kwargs.get("abs", _("on {time}")).replace("{time}", abs_time))}</span>')
