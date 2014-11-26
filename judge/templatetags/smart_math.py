from django.template import Library
from django.conf import settings
from django.utils.html import escape
from django.utils.http import urlquote

from judge.math_parser import MathHTMLParser


register = Library()

MATHTEX_CGI = getattr(settings, 'MATHTEX_CGI', 'http://www.forkosh.com/mathtex.cgi')


class MathJaxTexFallbackMath(MathHTMLParser):
    def inline_math(self, math):
        escaped = escape(math)
        return ('<span class="inline-math">'
                    r'<img class="tex-image" src="%s?\textstyle %s" alt="%s"/>'
                    r'<span class="tex-text" style="display:none">\(%s\)</span>'
                '</span>') % (MATHTEX_CGI, urlquote(math), escaped, escaped)

    def display_math(self, math):
        escaped = escape(math)
        return ('<span class="display-math">'
                   r'<img class="tex-image" src="%s?\displaystyle %s" alt="%s"/>'
                   r'<span class="tex-text" style="display:none">\[%s\]</span>'
                '</span>') % (MATHTEX_CGI, urlquote(math), escaped, escaped)


@register.filter(name='smart_math', is_safe=True)
def math(page):
    parser = MathJaxTexFallbackMath()
    parser.feed(page)
    return parser.result
