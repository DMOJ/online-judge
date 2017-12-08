from django.utils.html import avoid_wrapping

from . import registry


def _format_size(bytes, callback):
    bytes = float(bytes)

    KB = 1 << 10
    MB = 1 << 20
    GB = 1 << 30
    TB = 1 << 40
    PB = 1 << 50

    if bytes < KB:
        return callback('', bytes)
    elif bytes < MB:
        return callback('K', bytes / KB)
    elif bytes < GB:
        return callback('M', bytes / MB)
    elif bytes < TB:
        return callback('G', bytes / GB)
    elif bytes < PB:
        return callback('T', bytes / TB)
    else:
        return callback('P', bytes / PB)


@registry.filter
def kbdetailformat(bytes):
    return avoid_wrapping(_format_size(bytes * 1024, lambda x, y: ['%d %sB', '%.2f %sB'][bool(x)] % (y, x)))


@registry.filter
def kbsimpleformat(kb):
    return _format_size(kb * 1024, lambda x, y: '%.0f%s' % (y, x or 'B'))
