from textwrap import dedent

from django import forms
from django.conf import settings
from django.template import Context, Template
from lxml import html


class CompressorWidgetMixin(object):
    __template_css = dedent("""\
        {% compress css %}
            {{ media.css }}
        {% endcompress %}
    """)

    __template_js = dedent("""\
        {% compress js %}
            {{ media.js }}
        {% endcompress %}
    """)

    __templates = {
        (False, False): Template(''),
        (True, False): Template('{% load compress %}' + __template_css),
        (False, True): Template('{% load compress %}' + __template_js),
        (True, True): Template('{% load compress %}' + __template_js + __template_css),
    }

    compress_css = False
    compress_js = False

    try:
        import compressor
    except ImportError:
        pass
    else:
        if getattr(settings, 'COMPRESS_ENABLED', not settings.DEBUG):
            @property
            def media(self):
                media = super().media
                template = self.__templates[self.compress_css, self.compress_js]
                result = html.fromstring(template.render(Context({'media': media})))

                return forms.Media(
                    css={'all': [result.find('.//link').get('href')]} if self.compress_css else media._css,
                    js=[result.find('.//script').get('src')] if self.compress_js else media._js,
                )
