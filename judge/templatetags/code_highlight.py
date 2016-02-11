from django import template

from judge.highlight_code import highlight_code

register = template.Library()


@register.filter
def highlight(code, language):
    return highlight_code(code, language)
