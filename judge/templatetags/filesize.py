from django.template import Library
from django.utils.html import avoid_wrapping

register = Library()

@register.filter(is_safe=True)
def detailfilesizeformat(bytes):
    """
    Formats the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB,
    102 bytes, etc).
    """
    bytes = float(bytes)

    KB = 1 << 10
    MB = 1 << 20
    GB = 1 << 30
    TB = 1 << 40
    PB = 1 << 50

    if bytes < KB:
        value = '%d B' % bytes
    elif bytes < MB:
        value = '%.2f KB' % (bytes / KB)
    elif bytes < GB:
        value = '%.2f MB' % (bytes / MB)
    elif bytes < TB:
        value = '%.2f GB' % (bytes / GB)
    elif bytes < PB:
        value = '%.2f TB' % (bytes / TB)
    else:
        value = '%.2f PB' % (bytes / PB)

    return avoid_wrapping(value)