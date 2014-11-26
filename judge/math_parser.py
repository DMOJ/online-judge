from HTMLParser import HTMLParser
import re

from django.conf import settings


MATHTEX_CGI = getattr(settings, 'MATHTEX_CGI', 'http://www.forkosh.com/mathtex.cgi')
inline_math = re.compile(r'~(.*?)~|\\\((.*?)\\\)')
display_math = re.compile(r'\$\$(.*?)\$\$|\\\[(.*?)\\\]')


REPLACES = [
    (u'\u2264', r'\le'),
    (u'\u2265', r'\ge'),
    (u'\u2026', '...'),
    ('&le;', r'\le'),
    ('&le;', r'\ge'),
    (r'\lt', '<'),
    (r'\gt', '>'),
]


def format_math(math):
    for a, b in REPLACES:
        math = math.replace(a, b)
    return math


class MathHTMLParser(HTMLParser):
    @classmethod
    def convert(cls, html):
        converter = cls()
        converter.feed(html)
        return converter.result

    def __init__(self):
        HTMLParser.__init__(self)
        self.new_page = []
        self.data_buffer = []

    def _sub_inline(self, match):
        return self.inline_math(format_math(match.group(1) or match.group(2)))

    def _sub_display(self, match):
        return self.display_math(format_math(match.group(1) or match.group(2)))

    def inline_math(self, math):
        raise NotImplementedError()

    def display_math(self, math):
        raise NotImplementedError()

    @property
    def result(self):
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
