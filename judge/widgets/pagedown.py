from django.forms.utils import flatatt
from django.template.loader import get_template
from django.utils.encoding import force_str
from django.utils.html import conditional_escape

from judge.widgets.mixins import CompressorWidgetMixin

__all__ = ['PagedownWidget', 'MathJaxPagedownWidget', 'HeavyPreviewPageDownWidget']

try:
    from pagedown.widgets import PagedownWidget as OldPagedownWidget
except ImportError:
    PagedownWidget = None
    MathJaxPagedownWidget = None
    HeavyPreviewPageDownWidget = None
else:
    class PagedownWidget(CompressorWidgetMixin, OldPagedownWidget):
        # The goal here is to compress all the pagedown JS into one file.
        # We do not want any further compress down the chain, because
        # 1. we'll create multiple large JS files to download.
        # 2. this is not a problem here because all the pagedown JS files will be used together.
        compress_js = True

        def __init__(self, *args, **kwargs):
            kwargs.setdefault('css', ())
            super(PagedownWidget, self).__init__(*args, **kwargs)


    class MathJaxPagedownWidget(PagedownWidget):
        class Media:
            js = [
                'mathjax_config.js',
                'https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.0/es5/tex-chtml.min.js',
                'pagedown_math.js',
            ]


    class HeavyPreviewPageDownWidget(PagedownWidget):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault('template', 'pagedown.html')
            self.preview_url = kwargs.pop('preview')
            self.preview_timeout = kwargs.pop('preview_timeout', None)
            self.hide_preview_button = kwargs.pop('hide_preview_button', False)
            super(HeavyPreviewPageDownWidget, self).__init__(*args, **kwargs)

        def render(self, name, value, attrs=None, renderer=None):
            if value is None:
                value = ''
            final_attrs = self.build_attrs(attrs, {'name': name})
            if 'class' not in final_attrs:
                final_attrs['class'] = ''
            final_attrs['class'] += ' wmd-input'
            return get_template(self.template).render(self.get_template_context(final_attrs, value))

        def get_template_context(self, attrs, value):
            return {
                'attrs': flatatt(attrs),
                'body': conditional_escape(force_str(value)),
                'id': attrs['id'],
                'show_preview': self.show_preview,
                'preview_url': self.preview_url,
                'preview_timeout': self.preview_timeout,
                'extra_classes': 'dmmd-no-button' if self.hide_preview_button else None,
            }

        class Media:
            js = ['dmmd-preview.js']
