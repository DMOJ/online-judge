from django.template.defaultfilters import floatformat
from django.utils.html import avoid_wrapping
from django.utils.translation import gettext_lazy as _

from . import registry


def _format_size(bytes, formats, decimals):
    bytes = float(bytes)

    KB = 1 << 10
    MB = 1 << 20
    GB = 1 << 30
    TB = 1 << 40
    PB = 1 << 50

    if bytes < KB:
        return formats[0] % floatformat(bytes, decimals[0])
    elif bytes < MB:
        return formats[1] % floatformat(bytes / KB, decimals[1])
    elif bytes < GB:
        return formats[2] % floatformat(bytes / MB, decimals[2])
    elif bytes < TB:
        return formats[3] % floatformat(bytes / GB, decimals[3])
    elif bytes < PB:
        return formats[4] % floatformat(bytes / TB, decimals[4])
    else:
        return formats[5] % floatformat(bytes / PB, decimals[5])


@registry.filter
def kbdetailformat(kb):
    formats = [_('%s B'), _('%s KB'), _('%s MB'), _('%s GB'), _('%s TB'), _('%s PB')]
    decimals = [0, 2, 2, 2, 2, 2]
    return avoid_wrapping(_format_size(kb * 1024, formats, decimals))


@registry.filter
def kbsimpleformat(kb):
    formats = [_('%sB'), _('%sK'), _('%sM'), _('%sG'), _('%sT'), _('%sP')]
    decimals = [0, 0, 0, 0, 0, 0]
    return _format_size(kb * 1024, formats, decimals)
