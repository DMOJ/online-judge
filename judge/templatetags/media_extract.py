from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='media_type')
def media_type(media, type):
    return mark_safe('\n'.join(getattr(media, 'render_' + type)()))
