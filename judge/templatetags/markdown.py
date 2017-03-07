import hmac
from hashlib import sha1

import mistune
from django import template
from django.conf import settings
from judge.templatetags.camo_proxy import client as camo_client

from django.utils.safestring import mark_safe

from judge.highlight_code import highlight_code

register = template.Library()


class CodeSafeInlineGrammar(mistune.InlineGrammar):
    double_emphasis = re.compile(
        r'^\*{2}([\s\S]+?)()\*{2}(?!\*)'  # **word**
    )
    emphasis = re.compile(
        r'^\*((?:\*\*|[^\*])+?)()\*(?!\*)'  # *word*
    )


class CodeSafeInlineInlineLexer(mistune.InlineLexer):
    grammar_class = CodeSafeInlineGrammar


class AwesomeRenderer(mistune.Renderer):
    def __init__(self, *args, **kwargs):
        super(AwesomeRenderer, self).__init__(*args, **kwargs)

    def image(self, src, title, text):
        if camo_client:
            src = camo_client.image_url(src)
        super(AwesomeRenderer, self).image(src, title, text)

    def block_code(self, code, lang):
        if not lang:
            return '\n<pre><code>%s</code></pre>\n' % mistune.escape(code).rstrip()
        return highlight_code(code, lang)

    def header(self, text, level, *args, **kwargs):
        return super(AwesomeRenderer, self).header(text, level + 2, *args, **kwargs)


def markdown(value, style):
    styles = getattr(settings, 'MARKDOWN_STYLES', {}).get(style, getattr(settings, 'MARKDOWN_DEFAULT_STYLE', {}))
    escape = styles.get('safe_mode', 'escape') == 'escape'
    renderer = AwesomeRenderer(escape=escape)
    markdown = mistune.Markdown(renderer=renderer, inline=CodeSafeInlineInlineLexer(renderer))
    return markdown(value)


@register.filter(name='markdown')
def markdown_filter(value, style):
    return mark_safe(markdown(value, style))
