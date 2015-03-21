from django import template
register = template.Library()

from judge.ratings import rating_class, rating_name


@register.filter(name='rating_class')
def get_class(rating):
    return rating_class(int(rating))


@register.filter(name='rating_name')
def get_name(rating):
    return rating_name(int(rating))
