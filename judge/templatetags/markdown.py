import re

from django import template
import mistune
from django.conf import settings
from judge.highlight_code import highlight_code

register = template.Library()


class CodeSafeInlineGrammar(mistune.InlineGrammar):
    emphasis = re.compile(
        r'^\*((?:\*\*|[^\*])+?)\*(?!\*)'  # *word*
    )


class CodeSafeInlineInlineLexer(mistune.InlineLexer):
    grammar = CodeSafeInlineGrammar


class HighlightRenderer(mistune.Renderer):
    def block_code(self, code, lang):
        if not lang:
            return '\n<pre><code>%s</code></pre>\n' % mistune.escape(code).rstrip()
        return highlight_code(code, lang)

    def header(self, text, level, *args, **kwargs):
        return super(HighlightRenderer, self).header(text, level + 2, *args, **kwargs)


def markdown(value, style):
    styles = getattr(settings, 'MARKDOWN_STYLES', {}).get(style, getattr(settings, 'MARKDOWN_DEFAULT_STYLE', {}))
    escape = styles.get('safe_mode', 'escape') == 'escape'
    renderer = HighlightRenderer(escape=escape)
    markdown = mistune.Markdown(renderer=renderer, inline=CodeSafeInlineInlineLexer())
    return markdown(value)


@register.filter(name='markdown')
def markdown_filter(value, style):
    return markdown(value, style)
