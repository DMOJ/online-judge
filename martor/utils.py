from django.core.serializers.json import DjangoJSONEncoder
from django.utils.encoding import force_str
from django.utils.functional import Promise


class LazyEncoder(DjangoJSONEncoder):
    """
    This problem because we found error encoding,
    as docs says, django has special `DjangoJSONEncoder`
    at https://docs.djangoproject.com/en/1.10/topics/serialization/#serialization-formats-json
    also discused in this answer: http://stackoverflow.com/a/31746279/6396981

    Usage:
        >>> data = {}
        >>> json.dumps(data, cls=LazyEncoder)
    """

    def default(self, obj):
        if isinstance(obj, Promise):
            return force_str(obj)
        return super(LazyEncoder, self).default(obj)
