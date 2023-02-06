# -*- coding: utf-8 -*-
"""
Select2 Widgets based on https://github.com/applegrew/django-select2.

These components are responsible for rendering
the necessary HTML data markups. Since this whole
package is to render choices using Select2 JavaScript
library, hence these components are meant to be used
with choice fields.

Widgets are generally of two types:

    1. **Light** --
    They are not meant to be used when there
    are too many options, say, in thousands.
    This is because all those options would
    have to be pre-rendered onto the page
    and JavaScript would be used to search
    through them. Said that, they are also one
    the most easiest to use. They are a
    drop-in-replacement for Django's default
    select widgets.

    2. **Heavy** --
    They are suited for scenarios when the number of options
    are large and need complex queries (from maybe different
    sources) to get the options.
    This dynamic fetching of options undoubtedly requires
    Ajax communication with the server. Django-Select2 includes
    a helper JS file which is included automatically,
    so you need not worry about writing any Ajax related JS code.
    Although on the server side you do need to create a view
    specifically to respond to the queries.

Heavy widgets have the word 'Heavy' in their name.
Light widgets are normally named, i.e. there is no
'Light' word in their names.

"""
from copy import copy
from itertools import chain

from django import forms
from django.conf import settings
from django.core import signing
from django.forms.models import ModelChoiceIterator
from django.urls import reverse_lazy

__all__ = ['Select2Widget', 'Select2MultipleWidget', 'Select2TagWidget',
           'HeavySelect2Widget', 'HeavySelect2MultipleWidget', 'HeavySelect2TagWidget',
           'AdminSelect2Widget', 'AdminSelect2MultipleWidget', 'AdminHeavySelect2Widget',
           'AdminHeavySelect2MultipleWidget']


class Select2Mixin(object):
    """
    The base mixin of all Select2 widgets.

    This mixin is responsible for rendering the necessary
    data attributes for select2 as well as adding the static
    form media.
    """

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2 data attributes."""
        attrs = super(Select2Mixin, self).build_attrs(base_attrs, extra_attrs)
        attrs.setdefault('data-theme', settings.DMOJ_SELECT2_THEME)
        if self.is_required:
            attrs.setdefault('data-allow-clear', 'false')
        else:
            attrs.setdefault('data-allow-clear', 'true')
            attrs.setdefault('data-placeholder', '')

        attrs.setdefault('data-minimum-input-length', 0)
        if 'class' in attrs:
            attrs['class'] += ' django-select2'
        else:
            attrs['class'] = 'django-select2'
        return attrs

    def optgroups(self, name, value, attrs=None):
        """Add empty option for clearable selects."""
        if not self.is_required and not self.allow_multiple_selected:
            self.choices = list(chain([('', '')], self.choices))
        return super(Select2Mixin, self).optgroups(name, value, attrs=attrs)

    @property
    def media(self):
        """
        Construct Media as a dynamic property.

        .. Note:: For more information visit
            https://docs.djangoproject.com/en/1.8/topics/forms/media/#media-as-a-dynamic-property
        """
        return forms.Media(
            js=[settings.SELECT2_JS_URL, 'django_select2.js'],
            css={'screen': [settings.SELECT2_CSS_URL]},
        )


class AdminSelect2Mixin(Select2Mixin):
    @property
    def media(self):
        return forms.Media(
            js=['admin/js/jquery.init.js', settings.SELECT2_JS_URL, 'django_select2.js'],
            css={'screen': [settings.SELECT2_CSS_URL, 'select2-dmoj.css']},
        )


class Select2TagMixin(object):
    """Mixin to add select2 tag functionality."""

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add select2's tag attributes."""
        extra_attrs = extra_attrs or {}
        extra_attrs.setdefault('data-minimum-input-length', 1)
        extra_attrs.setdefault('data-tags', 'true')
        extra_attrs.setdefault('data-token-separators', [',', ' '])
        return super(Select2TagMixin, self).build_attrs(base_attrs, extra_attrs)


class Select2Widget(Select2Mixin, forms.Select):
    """
    Select2 drop in widget.

    Example usage::

        class MyModelForm(forms.ModelForm):
            class Meta:
                model = MyModel
                fields = ('my_field', )
                widgets = {
                    'my_field': Select2Widget
                }

    or::

        class MyForm(forms.Form):
            my_choice = forms.ChoiceField(widget=Select2Widget)

    """

    pass


class Select2MultipleWidget(Select2Mixin, forms.SelectMultiple):
    """
    Select2 drop in widget for multiple select.

    Works just like :class:`.Select2Widget` but for multi select.
    """

    pass


class Select2TagWidget(Select2TagMixin, Select2Mixin, forms.SelectMultiple):
    """
    Select2 drop in widget for for tagging.

    Example for :class:`.django.contrib.postgres.fields.ArrayField`::

        class MyWidget(Select2TagWidget):

            def value_from_datadict(self, data, files, name):
                values = super(MyWidget, self).value_from_datadict(data, files, name):
                return ",".join(values)

    """

    pass


class HeavySelect2Mixin(Select2Mixin):
    """Mixin that adds select2's ajax options."""

    def __init__(self, attrs=None, choices=(), **kwargs):
        self.choices = choices
        if attrs is not None:
            self.attrs = attrs.copy()
        else:
            self.attrs = {}

        self.data_view = kwargs.pop('data_view', None)
        self.data_url = kwargs.pop('data_url', None)

        if not (self.data_view or self.data_url):
            raise ValueError('You must ether specify "data_view" or "data_url".')

    def get_url(self):
        """Return url from instance or by reversing :attr:`.data_view`."""
        if self.data_url:
            return self.data_url
        return reverse_lazy(self.data_view)

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Set select2's ajax attributes."""
        attrs = super(HeavySelect2Mixin, self).build_attrs(base_attrs, extra_attrs)

        # encrypt instance Id
        self.widget_id = signing.dumps(id(self))

        attrs['data-field_id'] = self.widget_id
        attrs.setdefault('data-ajax--url', self.get_url())
        attrs.setdefault('data-ajax--cache', 'true')
        attrs.setdefault('data-ajax--type', 'GET')
        attrs.setdefault('data-minimum-input-length', 2)

        attrs['class'] += ' django-select2-heavy'
        return attrs

    def format_value(self, value):
        result = super(HeavySelect2Mixin, self).format_value(value)
        if isinstance(self.choices, ModelChoiceIterator):
            chosen = copy(self.choices)
            chosen.queryset = chosen.queryset.filter(pk__in=[
                int(i) for i in result if isinstance(i, int) or i.isdigit()
            ])
            # https://code.djangoproject.com/ticket/33155
            self.choices = {(value if isinstance(value, str) else value.value, label) for value, label in chosen}
        return result


class HeavySelect2Widget(HeavySelect2Mixin, forms.Select):
    """
    Select2 widget with AJAX support.

    Usage example::

        class MyWidget(HeavySelectWidget):
            data_view = 'my_view_name'

    or::

        class MyForm(forms.Form):
            my_field = forms.ChoicesField(
                widget=HeavySelectWidget(
                    data_url='/url/to/json/response'
                )
            )

    """

    pass


class HeavySelect2MultipleWidget(HeavySelect2Mixin, forms.SelectMultiple):
    """Select2 multi select widget similar to :class:`.HeavySelect2Widget`."""

    pass


class HeavySelect2TagWidget(Select2TagMixin, HeavySelect2MultipleWidget):
    """Select2 tag widget."""

    pass


class AdminSelect2Widget(AdminSelect2Mixin, Select2Widget):
    pass


class AdminSelect2MultipleWidget(AdminSelect2Mixin, Select2MultipleWidget):
    pass


class AdminHeavySelect2Widget(AdminSelect2Mixin, HeavySelect2Widget):
    pass


class AdminHeavySelect2MultipleWidget(AdminSelect2Mixin, HeavySelect2MultipleWidget):
    pass
