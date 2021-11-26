import datetime

from django.utils.translation import ngettext, npgettext, pgettext


def nice_repr(timedelta, display='long', sep=', '):
    """
    Turns a datetime.timedelta object into a nice string repr.

    display can be 'minimal', 'short' or 'long' [default].

    >>> from datetime import timedelta as td
    >>> nice_repr(td(days=1, hours=2, minutes=3, seconds=4))
    '1 day, 2 hours, 3 minutes, 4 seconds'
    >>> nice_repr(td(days=1, seconds=1), 'minimal')
    '1d, 1s'
    """

    assert isinstance(timedelta, datetime.timedelta), 'First argument must be a timedelta.'

    result = []

    weeks = timedelta.days // 7
    days = timedelta.days % 7
    hours = timedelta.seconds // 3600
    minutes = (timedelta.seconds % 3600) // 60
    seconds = timedelta.seconds % 60

    if display == 'simple-no-seconds':
        days += weeks * 7
        if days:
            if hours or minutes:
                return '%d day%s %d:%02d' % (days, 's'[days == 1:], hours, minutes)
            return '%d day%s' % (days, 's'[days == 1:])
        else:
            return '%d:%02d' % (hours, minutes)
    elif display == 'sql':
        days += weeks * 7
        return '%d %02d:%02d:%02d' % (days, hours, minutes, seconds)
    elif display == 'simple':
        days += weeks * 7
        if days:
            return '%d day%s %02d:%02d:%02d' % (days, 's'[days == 1:], hours, minutes, seconds)
        else:
            return '%02d:%02d:%02d' % (hours, minutes, seconds)
    elif display == 'localized':
        days += weeks * 7
        if days:
            return npgettext('time format with day', '%d day %h:%m:%s', '%d days %h:%m:%s', days) \
                .replace('%d', str(days)).replace('%h', '%02d' % hours).replace('%m', '%02d' % minutes) \
                .replace('%s', '%02d' % seconds)
        else:
            return pgettext('time format without day', '%h:%m:%s') \
                .replace('%h', '%02d' % hours).replace('%m', '%02d' % minutes).replace('%s', '%02d' % seconds)
    elif display == 'localized-no-seconds':
        days += weeks * 7
        if days:
            if hours or minutes:
                return npgettext('time format no seconds with day', '%d day %h:%m', '%d days %h:%m', days) \
                    .replace('%d', str(days)).replace('%h', '%02d' % hours).replace('%m', '%02d' % minutes)
            return ngettext('%d day', '%d days', days) % days
        else:
            return pgettext('hours and minutes', '%h:%m').replace('%h', '%02d' % hours).replace('%m', '%02d' % minutes)
    elif display == 'concise':
        days += weeks * 7
        if days:
            return '%dd %02d:%02d:%02d' % (days, hours, minutes, seconds)
        else:
            return '%02d:%02d:%02d' % (hours, minutes, seconds)
    elif display == 'noday':
        days += weeks * 7
        hours += days * 24
        return '%02d:%02d:%02d' % (hours, minutes, seconds)
    elif display == 'minimal':
        words = ['w', 'd', 'h', 'm', 's']
    elif display == 'short':
        words = [' wks', ' days', ' hrs', ' min', ' sec']
    else:
        words = [' weeks', ' days', ' hours', ' minutes', ' seconds']

    values = [weeks, days, hours, minutes, seconds]

    for i in range(len(values)):
        if values[i]:
            if values[i] == 1 and len(words[i]) > 1:
                result.append('%i%s' % (values[i], words[i].rstrip('s')))
            else:
                result.append('%i%s' % (values[i], words[i]))

    return sep.join(result)
