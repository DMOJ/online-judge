from django.utils.html import format_html

from . import registry


@registry.function
def bold(text):
    return format_html('<b>{0}</b>', text)
