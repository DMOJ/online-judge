import re

from django.conf import settings
from lxml import html
from lxml.etree import ElementBase

from judge import lxml_tree

INLINE_MATH_PNG = getattr(settings, 'INLINE_MATH_PNG', 'http://www.forkosh.com/mathtex.cgi')
DISPLAY_MATH_PNG = getattr(settings, 'DISPLAY_MATH_PNG', INLINE_MATH_PNG)
INLINE_MATH_SVG = getattr(settings, 'INLINE_MATH_SVG', INLINE_MATH_PNG)
DISPLAY_MATH_SVG = getattr(settings, 'DISPLAY_MATH_SVG', DISPLAY_MATH_PNG)

inline_math = re.compile(r'~(.*?)~|\\\((.*?)\\\)')
display_math = re.compile(r'\$\$(.*?)\$\$|\\\[(.*?)\\\]')


REPLACES = [
    (u'\u2264', r'\le'),
    (u'\u2265', r'\ge'),
    (u'\u2026', '...'),
    (u'\u2212', '-'),
    ('&le;', r'\le'),
    ('&le;', r'\ge'),
    ('&lt;', '<'),
    ('&gt;', '>'),
    ('&amp;', '&'),
    ('&#8722;', '-'),
    ('&#8804;', r'\le'),
    ('&#8805;', r'\ge'),
    ('&#8230;', '...'),
    (r'\lt', '<'),
    (r'\gt', '>'),
]


def format_math(math):
    for a, b in REPLACES:
        math = math.replace(a, b)
    return math


class MathHTMLParser(object):
    def __init__(self):
        pass

    def _sub_inline(self, match):
        return self.inline_math(format_math(match.group(1) or match.group(2) or ''))

    def _sub_display(self, match):
        return self.display_math(format_math(match.group(1) or match.group(2) or ''))

    def inline_math(self, math):
        raise NotImplementedError()

    def display_math(self, math):
        raise NotImplementedError()

    def process(self, text):
        doc = lxml_tree.fromstring(text)

        for block in doc.xpath('//text()'):
            result = inline_math.sub(self._sub_inline, block)
            result = display_math.sub(self._sub_display, result)
            last = block.getparent()
            into_text = block.is_text

            if into_text:
                last.text = ''
            else:
                last.tail = ''

            for item in html.fragments_fromstring(result):
                if isinstance(item, ElementBase):
                    if into_text:
                        last.insert(0, item)
                    else:
                        last.addnext(item)
                    last = item
                    into_text = False
                elif into_text:
                    block.text += item
                else:
                    block.tail = item + block.tail

        return doc

    @classmethod
    def convert(cls, html, *args, **kwargs):
        return cls(*args, **kwargs).process(html)
