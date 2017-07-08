from django import forms
from django.core.exceptions import FieldError
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe


class CheckboxSelectMultipleWithSelectAll(forms.CheckboxSelectMultiple):
    _all_selected = False

    def render(self, name, value, attrs=None, original=None):
        if 'id' not in attrs:
            raise FieldError('id required')

        select_all_id = attrs['id'] + '_all'
        select_all_name = name + '_all'
        original = super(CheckboxSelectMultipleWithSelectAll, self).render(name, value, attrs, original)
        template = get_template('widgets/select_all.jade')
        context = Context({'original_widget': original,
                           'select_all_id': select_all_id,
                           'select_all_name': select_all_name,
                           'all_selected': all(choice[0] in value for choice in self.choices),
                           'empty': not self.choices})
        return mark_safe(template.render(context))

    def value_from_datadict(self, *args, **kwargs):
        original = super(CheckboxSelectMultipleWithSelectAll, self).value_from_datadict(*args, **kwargs)
        select_all_name = args[2] + '_all'
        if select_all_name in args[0]:
            self._all_selected = True
        else:
            self._all_selected = False
        return original
