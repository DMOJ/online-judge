import datetime

from judge.utils.timedelta import nice_repr
from . import registry


@registry.filter
def timedelta(value, display='long'):
    if value is None:
        return value
    return nice_repr(value, display)


@registry.filter
def timestampdelta(value, display='long'):
    value = datetime.timedelta(seconds=value)
    return timedelta(value, display)


@registry.filter
def seconds(timedelta):
    return timedelta.total_seconds()


@registry.function
@registry.render_with('time-remaining-fragment.html')
def as_countdown(timedelta):
    return {'countdown': timedelta}
