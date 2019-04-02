from itertools import count

from django import template

register = template.Library()


@register.simple_tag
def get_counter(start=1):
    return count(start).__next__
