def safe_int_or_none(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_float_or_none(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
