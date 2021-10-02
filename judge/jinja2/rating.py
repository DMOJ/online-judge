from judge.ratings import rating_class, rating_name, rating_progress
from . import registry


def _get_rating_value(func, obj):
    if obj is None:
        return None

    if isinstance(obj, int):
        return func(obj)
    else:
        return func(obj.rating)


@registry.function('rating_class')
def get_rating_class(obj):
    return _get_rating_value(rating_class, obj) or 'rate-none'


@registry.function(name='rating_name')
def get_name(obj):
    return _get_rating_value(rating_name, obj) or 'Unrated'


@registry.function(name='rating_progress')
def get_progress(obj):
    return _get_rating_value(rating_progress, obj) or 0.0


@registry.function
@registry.render_with('user/rating.html')
def rating_number(obj):
    return {'rating': obj}
