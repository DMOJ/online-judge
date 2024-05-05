import html

from django.utils.html import escapejs, format_html

from . import registry


@registry.function
def bold(text):
    return format_html('<b>{0}</b>', text)


@registry.filter
def htmltojs(text):
    return format_html("'{0}'", escapejs(html.unescape(text)))
