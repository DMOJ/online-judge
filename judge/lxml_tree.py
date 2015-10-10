import logging

from django.utils.safestring import mark_safe
from lxml import html
from lxml.etree import ParserError, XMLSyntaxError

logger = logging.getLogger('judge.html')


class HTMLTreeString(object):
    def __init__(self, str):
        try:
            self._tree = html.fromstring(str, parser=html.HTMLParser(recover=True))
        except (XMLSyntaxError, ParserError) as e:
            if str and (not ininstance(ParserError) or i.args[0] != 'Document is empty'):
                logger.exception('Failed to parse HTML string')
            self._tree = html.Element('div')

    def __getattr__(self, attr):
        try:
            return getattr(self._tree, attr)
        except AttributeError:
            return getattr(unicode(self), attr)

    def __setattr__(self, key, value):
        if key[0] == '_':
            super(HTMLTreeString, self).__setattr__(key, value)
        setattr(self._tree, key, value)

    def __repr__(self):
        return '<HTMLTreeString %r>' % str(self)

    def __str__(self):
        return mark_safe(html.tostring(self._tree))

    def __unicode__(self):
        return mark_safe(html.tostring(self._tree, encoding='unicode'))

    def __radd__(self, other):
        if isinstance(other, str):
            return other + str(self)
        return other + unicode(self)

    def __add__(self, other):
        if isinstance(other, str):
            return str(self) + other
        return unicode(self) + other


def fromstring(str):
    if isinstance(str, HTMLTreeString):
        return str
    return HTMLTreeString(str)
