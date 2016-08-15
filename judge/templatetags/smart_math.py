from django.conf import settings
from django.template import Library
from django.utils.html import escape, format_html
from django.utils.http import urlquote

from judge.math_parser import MathHTMLParser, INLINE_MATH_PNG, INLINE_MATH_SVG, \
    DISPLAY_MATH_PNG, DISPLAY_MATH_SVG
from judge.utils.mathoid import MathoidMathParser

register = Library()


class SmartSVGMath(MathHTMLParser):
    def inline_math(self, math):
        return format_html(ur'<img class="inline-math" src="{0}?\textstyle {2}" '
                           ur'''onerror="this.src=\'{1}?\textstyle {2}\'" alt="{3}"/>''',
                           INLINE_MATH_SVG, INLINE_MATH_PNG, urlquote(math), math)

    def display_math(self, math):
        return format_html(ur'<img class="display-math" src="{0}?\displaystyle {2}" '
                           ur'''onerror="this.src=\'{1}?\displaystyle {2}\'" alt="{3}"/>''',
                           INLINE_MATH_SVG, INLINE_MATH_PNG, urlquote(math), math)


class MathJaxSmartSVGFallbackMath(MathHTMLParser):
    def inline_math(self, math):
        return format_html(u'<span class="inline-math">'
                           ur'<img class="tex-image" src="{0}?\textstyle {2}" '
                           ur'''onerror="this.src=\'{1}?\textstyle {2}\'" alt="{3}"/>'''
                           ur'<span class="tex-text" style="display:none">~{3}~</span>'
                           u'</span>', INLINE_MATH_SVG, INLINE_MATH_PNG, urlquote(math), math)

    def display_math(self, math):
        return format_html(u'<span class="display-math">'
                           ur'<img class="tex-image" src="{0}?\displaystyle {2}" '
                           ur'''onerror="this.src=\'{1}?\displaystyle {2}\'" alt="{3}"/>'''
                           ur'<span class="tex-text" style="display:none">$${3}$$</span>'
                           u'</span>', DISPLAY_MATH_SVG, DISPLAY_MATH_PNG, urlquote(math), math)


class TexOnlyMath(MathHTMLParser):
    def inline_math(self, math):
        return '~%s~' % escape(math)

    def display_math(self, math):
        return '$$%s$$' % escape(math)


@register.filter(name='smart_math', is_safe=True)
def math(page, engine):
    if hasattr(settings, 'MATHOID_URL'):
        return MathoidMathParser.convert(page, engine)
    else:
        return {'jax': MathJaxSmartSVGFallbackMath,
                'mml': MathJaxSmartSVGFallbackMath,
                'tex': TexOnlyMath,
                'svg': SmartSVGMath}[engine].convert(page)
