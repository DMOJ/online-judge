from HTMLParser import HTMLParser
from django.template import Library
from django.conf import settings
import re

register = Library()

MATHTEX_CGI = settings.get('MATHTEX_CGI', 'http://www.forkosh.com/mathtex.cgi')
inlinemath = re.compile(r'~(.*?)~|\\\((.*?)\\\)')


def inline_template(match):
    math = match.group(1) or match.group(2)
    return r'''
<span>
    <img src="%s?\textstyle %s"/>
    <span style="display:none">\( %s \)</span>
</span>
''' % (MATHTEX_CGI, math, math)

displaymath = re.compile('$$(.*?)$$|\\\[(.*?)\\\]')


def display_template(match):
    math = match.group(1) or match.group(2)
    return r'''
<span>
    <img src="%s?\displaystyle %s"/>
    <span style="display:none">\[ %s \]</div>
</span>
''' % (MATHTEX_CGI, math, math)


class MathHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.new_page = []
        self.data_buffer = []

    def purge_buffer(self):
        if self.data_buffer:
            buffer = ''.join(self.data_buffer)
            buffer = inlinemath.sub(inline_template, buffer)
            buffer = displaymath.sub(display_template, buffer)
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


@register.filter(name='smart_math', is_safe=True)
def math(page):
    parser = MathHTMLParser()
    parser.feed(page)
    return ''.join(parser.new_page)
