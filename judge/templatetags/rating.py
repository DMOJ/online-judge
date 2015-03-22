from django import template
register = template.Library()

from judge.ratings import rating_class, rating_name, rating_progress


@register.filter(name='rating_class')
def get_class(rating):
    return 'rate-none' if rating is None else rating_class(int(rating))


@register.filter(name='rating_name')
def get_name(rating):
    return 'Unrated' if rating is None else rating_name(int(rating))


@register.filter(name='rating_progress')
def get_progress(rating):
    return 0.0 if rating is None else rating_progress(int(rating))
