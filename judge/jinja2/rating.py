from django.utils import six
from django_jinja import library

from judge.ratings import rating_class


@library.global_function('rating_class')
def get_rating_class(obj):
    if isinstance(obj, six.integer_types):
        return rating_class(obj)
    else:
        return rating_class(obj.rating)
