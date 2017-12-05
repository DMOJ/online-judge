from django import forms
from django.core.exceptions import FieldError
from django.template.loader import get_template
from django.utils.safestring import mark_safe


class CheckboxSelectMultipleWithSelectAll(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, renderer=None):
        if 'id' not in attrs:
            raise FieldError('id required')

        select_all_id = attrs['id'] + '_all'
        select_all_name = name + '_all'
        original = super(CheckboxSelectMultipleWithSelectAll, self).render(name, value, attrs, renderer)
        template = get_template('widgets/select_all.html')
        return mark_safe(template.render({
            'original_widget': original,
            'select_all_id': select_all_id,
            'select_all_name': select_all_name,
            'all_selected': all(choice[0] in value for choice in self.choices) if value else False,
            'empty': not self.choices,
        }))
