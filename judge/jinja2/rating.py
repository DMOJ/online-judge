from django.utils import six

from judge.ratings import rating_class


def get_rating_class(obj):
    if isinstance(obj, six.integer_types):
        return rating_class(obj)
    else:
        return rating_class(obj.rating)
