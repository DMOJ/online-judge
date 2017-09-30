from django import template

from judge.ratings import rating_class, rating_name, rating_progress

register = template.Library()


@register.filter(name='rating_class')
def get_class(rating):
    return rating_class(int(rating)) if rating is not None else 'rate-none'


@register.filter(name='rating_name')
def get_name(rating):
    return rating_name(int(rating)) if rating is not None else 'Unrated'


@register.filter(name='rating_progress')
def get_progress(rating):
    return rating_progress(int(rating)) if rating else 0.0
