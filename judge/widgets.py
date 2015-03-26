from django import forms
from django.contrib.staticfiles.storage import staticfiles_storage
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.core.exceptions import FieldError


class CheckboxSelectMultipleWithSelectAll(forms.CheckboxSelectMultiple):
    _all_selected = False

    def render(self, *args, **kwargs):
        empty = False
        if not self.choices:
            empty = True
        has_id = kwargs and ('attrs' in kwargs) and ('id' in kwargs['attrs'])
        if not has_id:
            raise FieldError('id required')
        select_all_id = kwargs['attrs']['id'] + '_all'
        select_all_name = args[0] + '_all'
        renderer = super(CheckboxSelectMultipleWithSelectAll, self).get_renderer(*args, **kwargs)
        template = get_template('widgets/select_all.jade')
        context = Context({'original_widget': renderer.render(),
                           'select_all_id': select_all_id,
                           'select_all_name': select_all_name,
                           'all_selected': all(choice[0] in renderer.value for choice in renderer.choices),
                           'empty': empty})
        return mark_safe(template.render(context))

    def value_from_datadict(self, *args, **kwargs):
        original = super(CheckboxSelectMultipleWithSelectAll, self).value_from_datadict(*args, **kwargs)
        select_all_name = args[2] + '_all'
        if select_all_name in args[0]:
            self._all_selected = True
        else:
            self._all_selected = False
        return original

try:
    from pagedown.widgets import PagedownWidget, AdminPagedownWidget
except ImportError:
    PagedownWidget = None
    AdminPagedownWidget = None
    MathJaxPagedownWidget = None
    MathJaxAdminPagedownWidget = None
else:
    class BaseMathJaxPagedownWidget(PagedownWidget):
        @property
        def media(self):
            media = self._media()
            media.add_js([
                staticfiles_storage.url('mathjax_config.js'),
                '//cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML',
                staticfiles_storage.url('pagedown_math.js'),
            ])
            return media

    class MathJaxPagedownWidget(BaseMathJaxPagedownWidget):
        @property
        def media(self):
            media = super(MathJaxPagedownWidget, self).media()
            media.add_css([staticfiles_storage.url('pagedown_widget.css')])
            return media

    class MathJaxAdminPagedownWidget(AdminPagedownWidget, BaseMathJaxPagedownWidget):
        pass