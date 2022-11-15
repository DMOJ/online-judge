from math import isfinite


def safe_int_or_none(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_float_or_none(value, force_finite=True):
    try:
        num = float(value)
    except (ValueError, TypeError):
        return None

    if force_finite and not isfinite(num):
        return None

    return num
