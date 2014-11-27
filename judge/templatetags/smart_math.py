from django.template import Library
from django.utils.html import escape
from django.utils.http import urlquote

from judge.math_parser import MathHTMLParser, MATHTEX_CGI

register = Library()


class MathJaxTexFallbackMath(MathHTMLParser):
    def inline_math(self, math):
        return ('<span class="inline-math">'
                    r'<img class="tex-image" src="%s?\textstyle %s" alt="%s"/>'
                    r'<span class="tex-text" style="display:none">\(%s\)</span>'
                '</span>') % (MATHTEX_CGI, urlquote(math), math, math)

    def display_math(self, math):
        return ('<span class="display-math">'
                   r'<img class="tex-image" src="%s?\displaystyle %s" alt="%s"/>'
                   r'<span class="tex-text" style="display:none">\[%s\]</span>'
                '</span>') % (MATHTEX_CGI, urlquote(math), math, math)


@register.filter(name='smart_math', is_safe=True)
def math(page):
    return MathJaxTexFallbackMath.convert(page)
