import re

from django.core.exceptions import ValidationError
from django.db.models import SubfieldBase
from django.db.models.fields import TextField

RegexType = type(re.compile(''))


class RegexTextField(TextField):
    """
    A field that stores a regular expression and compiles it when accessed.

    Based off https://github.com/ambitioninc/django-regex-field.
    """
    description = 'A regular expression'
    __metaclass__ = SubfieldBase

    # Maintain a cache of compiled regexen for faster lookup
    compiled_regex_cache = {}

    def get_prep_value(self, value):
        value = self.to_python(value)
        return self.value_to_string(value)

    def get_compiled_regex(self, value):
        if value not in self.compiled_regex_cache:
            self.compiled_regex_cache[value] = re.compile(value, re.VERBOSE)
        return self.compiled_regex_cache[value]

    def to_python(self, value):
        """
        Handles the following cases:
        1. If the value is already the proper type (a regex), return it.
        2. If the value is a string, compile and return the regex.

        Raises: A ValidationError if the regex cannot be compiled.
        """
        if isinstance(value, RegexType):
            return value
        else:
            if value is None and self.null:
                return None
            else:
                try:
                    return self.get_compiled_regex(value)
                except:
                    raise ValidationError('Invalid regex {0}'.format(value))

    def value_to_string(self, obj):
        if obj is not None:
            return obj.pattern