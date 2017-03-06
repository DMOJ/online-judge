from django import template
import mistune
from django.conf import settings
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

register = template.Library()


class HighlightRenderer(mistune.Renderer):
    def block_code(self, code, lang):
        if not lang:
            return '\n<div class="codehilite"><pre><code>%s</code></pre></div>\n' % \
                   mistune.escape(code)
        lexer = get_lexer_by_name(lang, stripall=True)
        formatter = HtmlFormatter()
        return highlight(code, lexer, formatter)

    def header(self, text, level, *args, **kwargs):
        return super(HighlightRenderer, self).header(text, level + 2, *args, **kwargs)


def markdown(value, style):
    styles = getattr(settings, 'MARKDOWN_STYLES', {}).get(style, getattr(settings, 'MARKDOWN_DEFAULT_STYLE', {}))
    escape = styles.get('safe_mode', 'escape') == 'escape'
    renderer = HighlightRenderer()
    markdown = mistune.Markdown(escape=escape, renderer=renderer)
    return markdown(value)


@register.filter(name='markdown')
def markdown_filter(value, style):
    return markdown(value, style)
