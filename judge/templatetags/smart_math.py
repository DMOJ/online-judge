from django.template import Library
from django.utils.http import urlquote

from judge.math_parser import MathHTMLParser, INLINE_MATH_PNG, INLINE_MATH_SVG, \
    DISPLAY_MATH_PNG, DISPLAY_MATH_SVG, SVG_MATH_LEVEL

register = Library()


class MathJaxTexFallbackMath(MathHTMLParser):
    def inline_math(self, math):
        return ('<span class="inline-math">'
                    r'<img class="tex-image" src="%s?\textstyle %s" alt="%s"/>'
                    r'<span class="tex-text" style="display:none">~%s~</span>'
                '</span>') % (INLINE_MATH_PNG, urlquote(math), math, math)

    def display_math(self, math):
        return ('<span class="display-math">'
                   r'<img class="tex-image" src="%s?\displaystyle %s" alt="%s"/>'
                   r'<span class="tex-text" style="display:none">$$%s$$</span>'
                '</span>') % (DISPLAY_MATH_PNG, urlquote(math), math, math)


class MathJaxSmartSVGFallbackMath(MathHTMLParser):
    def __init__(self, agent):
        MathHTMLParser.__init__(self)
        self.use_svg = SVG_MATH_LEVEL == 2 or SVG_MATH_LEVEL == 1 and 'Firefox/' in agent

    def inline_math(self, math):
        return ('<span class="inline-math">'
                    r'<img class="tex-image" src="%s?\textstyle %s" alt="%s"/>'
                    r'<span class="tex-text" style="display:none">~%s~</span>'
                '</span>') % ((INLINE_MATH_PNG, INLINE_MATH_SVG)[self.use_svg],
                              urlquote(math), math, math)

    def display_math(self, math):
        return ('<span class="display-math">'
                   r'<img class="tex-image" src="%s?\displaystyle %s" alt="%s"/>'
                   r'<span class="tex-text" style="display:none">$$%s$$</span>'
                '</span>') % ((DISPLAY_MATH_PNG, DISPLAY_MATH_SVG)[self.use_svg], urlquote(math), math, math)


class MathJaxTexOnlyMath(MathHTMLParser):
    def inline_math(self, math):
        return '~%s~' % math

    def display_math(self, math):
        return '$$%s$$' % math


@register.filter(name='smart_math', is_safe=True)
def math(page, style='fallback'):
    if style == 'tex':
        return MathJaxTexOnlyMath.convert(page)
    else:
        return MathJaxTexFallbackMath.convert(page)

@register.filter(name='smart_svg_math', is_safe=True)
def math(page, user_agent):
    return MathJaxSmartSVGFallbackMath.convert(page, user_agent)