"""
Django-ace originally from https://github.com/bradleyayers/django-ace.
"""

from __future__ import unicode_literals
from urlparse import urljoin
from django import forms
from django.conf import settings

try:
    from django.forms.utils import flatatt
except ImportError:
    from django.forms.util import flatatt
from django.utils.safestring import mark_safe


ACE_URL = getattr(settings, 'ACE_URL', '//cdnjs.cloudflare.com/ajax/libs/ace/1.1.3/ext-split.js')


class AceWidget(forms.Textarea):
    def __init__(self, mode=None, theme=None, wordwrap=False, width='500px', height='300px', *args, **kwargs):
        self.mode = mode
        self.theme = theme
        self.wordwrap = wordwrap
        self.width = width
        self.height = height
        super(AceWidget, self).__init__(*args, **kwargs)

    @property
    def media(self):
        js = [
            urljoin(ACE_URL, 'ace.js'),
            'django_ace/widget.js',
        ]
        if self.mode:
            js.append(urljoin(ACE_URL, 'mode-%s.js' % self.mode))
        if self.theme:
            js.append(urljoin(ACE_URL, 'theme-%s.js' % self.theme))
        css = {
            'screen': ['django_ace/widget.css'],
        }
        return forms.Media(js=js, css=css)

    def render(self, name, value, attrs=None):
        attrs = attrs or {}

        ace_attrs = {
            'class': 'django-ace-widget loading',
            'style': 'width:%s; height:%s' % (self.width, self.height)
        }
        if self.mode:
            ace_attrs['data-mode'] = self.mode
        if self.theme:
            ace_attrs['data-theme'] = self.theme
        if self.wordwrap:
            ace_attrs['data-wordwrap'] = 'true'

        textarea = super(AceWidget, self).render(name, value, attrs)

        html = '<div%s><div></div></div>%s' % (flatatt(ace_attrs), textarea)

        # add toolbar
        html = ('<div class="django-ace-editor"><div style="width: %s" class="django-ace-toolbar">'
                '<a href="./" class="django-ace-max_min"></a></div>%s</div>') % (self.width, html)

        return mark_safe(html)
