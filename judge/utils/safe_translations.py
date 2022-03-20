from django.utils.html import escape


def _init():
    from functools import wraps
    from django.utils import translation

    def wrap(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            return escape(function(*args, **kwargs))

        return wrapper

    for func in ['gettext', 'gettext_lazy', 'gettext_noop', 'ngettext', 'ngettext_lazy', 'pgettext', 'pgettext_lazy']:
        globals()[func] = wrap(getattr(translation, func))


_init()
del _init
