from django import forms
from django.contrib.admin import widgets
from django.template.loader import get_template

from .settings import (
    MARTOR_ENABLE_CONFIGS,
    MARTOR_MARKDOWNIFY_URL,
    MARTOR_SEARCH_USERS_URL,
    MARTOR_UPLOAD_URL,
)


class MartorWidget(forms.Textarea):
    UPLOADS_ENABLED = False

    def render(self, name, value, attrs=None, renderer=None, **kwargs):
        # Make the settings the default attributes to pass
        attributes_to_pass = {
            'data-enable-configs': MARTOR_ENABLE_CONFIGS,
            'data-upload-url': MARTOR_UPLOAD_URL,
            'data-markdownfy-url': MARTOR_MARKDOWNIFY_URL,
            'data-search-users-url': MARTOR_SEARCH_USERS_URL,
        }

        # Make sure that the martor value is in the class attr passed in
        if 'class' in attrs:
            attrs['class'] += ' martor'
        else:
            attrs['class'] = 'martor'

        # Update and overwrite with the attributes passed in
        attributes_to_pass.update(attrs)

        # Update and overwrite with any attributes that are on the widget
        # itself. This is also the only way we can push something in without
        # being part of the render chain.
        attributes_to_pass.update(self.attrs)

        widget = super(MartorWidget, self).render(name, value, attributes_to_pass)

        template = get_template('martor/editor.html')
        mentions_enabled = MARTOR_ENABLE_CONFIGS.get('mention') == 'true'

        return template.render({
            'martor': widget,
            'field_name': name,
            'mentions_enabled': mentions_enabled,
            'uploads_enabled': self.UPLOADS_ENABLED,
        })

    class Media:
        css = {
            'all': (
                'plugins/css/ace.min.css',
                'plugins/css/semantic.css',
                'plugins/css/resizable.min.css',
            ),
        }
        js = (
            'plugins/js/ace.js',
            'plugins/js/semantic.min.js',
            'plugins/js/mode-markdown.js',
            'plugins/js/ext-language_tools.js',
            'plugins/js/theme-github.js',
            'plugins/js/theme-twilight.js',
            'plugins/js/highlight.min.js',
            'plugins/js/resizable.min.js',
            'martor/js/martor.js',
        )

        if MARTOR_ENABLE_CONFIGS.get('jquery') == 'true':
            js = ('plugins/js/jquery.min.js',).__add__(js)


class AdminMartorWidget(MartorWidget, widgets.AdminTextareaWidget):
    pass
