from django.utils.safestring import mark_safe
from lxml import html


class HTMLTreeString(object):
    def __init__(self, str):
        self._tree = html.fromstring(str)

    def __getattr__(self, attr):
        return getattr(self._tree, attr)

    def __setattr__(self, key, value):
        if key[0] == '_':
            super(HTMLTreeString, self).__setattr__(key, value)
        setattr(self._tree, key, value)

    def __str__(self):
        return mark_safe(html.tostring(self._tree))

    def __unicode__(self):
        return mark_safe(html.tostring(self._tree, encoding='unicode'))


def fromstring(str):
    if isinstance(str, HTMLTreeString):
        return str
    return HTMLTreeString(str)
