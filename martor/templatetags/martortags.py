from django import template
from django.utils.safestring import mark_safe

from ..utils import markdownify

register = template.Library()


@register.filter
def safe_markdown(field_name):
    """
    Safe the markdown text as html ouput.

    Usage:
        {% load martortags %}
        {{ field_name|safe_markdown }}

    Example:
        {{ post.description|safe_markdown }}
    """
    return mark_safe(markdownify(field_name))
