from HTMLParser import HTMLParser
import re

from django.conf import settings


INLINE_MATH_PNG = getattr(settings, 'INLINE_MATH_PNG', 'http://www.forkosh.com/mathtex.cgi')
DISPLAY_MATH_PNG = getattr(settings, 'DISPLAY_MATH_PNG', INLINE_MATH_PNG)
INLINE_MATH_SVG = getattr(settings, 'INLINE_MATH_SVG', INLINE_MATH_PNG)
DISPLAY_MATH_SVG = getattr(settings, 'DISPLAY_MATH_SVG', DISPLAY_MATH_PNG)
SVG_MATH_LEVEL = getattr(settings, 'SVG_MATH_LEVEL', 0)

inline_math = re.compile(r'~(.*?)~|\\\((.*?)\\\)')
display_math = re.compile(r'\$\$(.*?)\$\$|\\\[(.*?)\\\]')


REPLACES = [
    (u'\u2264', r'\le'),
    (u'\u2265', r'\ge'),
    (u'\u2026', '...'),
    (u'\u2212', '-'),
    ('&le;', r'\le'),
    ('&le;', r'\ge'),
    ('&lt;', r'<'),
    ('&gt;', r'>'),
    (r'\lt', '<'),
    (r'\gt', '>'),
]


def format_math(math):
    for a, b in REPLACES:
        math = math.replace(a, b)
    return math


class MathHTMLParser(HTMLParser):
    @classmethod
    def convert(cls, html, *args, **kwargs):
        converter = cls(*args, **kwargs)
        converter.feed(html)
        return converter.result

    def __init__(self):
        HTMLParser.__init__(self)
        self.new_page = []
        self.data_buffer = []

    def _sub_inline(self, match):
        return self.inline_math(format_math(match.group(1) or match.group(2) or ''))

    def _sub_display(self, match):
        return self.display_math(format_math(match.group(1) or match.group(2) or ''))

    def inline_math(self, math):
        raise NotImplementedError()

    def display_math(self, math):
        raise NotImplementedError()

    @property
    def result(self):
        self.purge_buffer()
        return ''.join(self.new_page)

    def purge_buffer(self):
        if self.data_buffer:
            buffer = ''.join(self.data_buffer)
            buffer = inline_math.sub(self._sub_inline, buffer)
            buffer = display_math.sub(self._sub_display, buffer)
            self.new_page.append(buffer)
            del self.data_buffer[:]

    def handle_starttag(self, tag, attrs):
        self.purge_buffer()
        self.new_page.append('<%s%s>' % (tag, ' '.join([''] + ['%s="%s"' % p for p in attrs])))

    def handle_endtag(self, tag):
        self.purge_buffer()
        self.new_page.append('</%s>' % tag)

    def handle_data(self, data):
        self.data_buffer.append(data)

    def handle_entityref(self, name):
        self.data_buffer.append('&%s;' % name)

    def handle_charref(self, name):
        self.data_buffer.append('&#%s;' % name)
