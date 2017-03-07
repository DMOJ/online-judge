import hmac
from hashlib import sha1
import re
from urlparse import urlparse

from django import template
import mistune
from django.conf import settings
from judge.templatetags.camo_proxy import client as camo_client

from django.utils.safestring import mark_safe

from judge.highlight_code import highlight_code

register = template.Library()

NOFOLLOW_WHITELIST = getattr(settings, 'NOFOLLOW_EXCLUDED', set())


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
        self.nofollow = kwargs.pop('nofollow', False)
        super(AwesomeRenderer, self).__init__(*args, **kwargs)

    def image(self, src, title, text):
        if camo_client:
            src = camo_client.image_url(src)
        super(AwesomeRenderer, self).image(src, title, text)

    def _link_rel(self, href):
        if href:
            url = urlparse(href)
            if url.netloc and url.netloc not in NOFOLLOW_WHITELIST:
                return 'rel="nofollow"'
        return ''

    def autolink(self, link, is_email=False):
        text = link = mistune.escape(link)
        if is_email:
            link = 'mailto:%s' % link
        return '<a href="%s" %s>%s</a>' % (link, text, self._link_rel(link))

    def link(self, link, title, text):
        link = mistune.escape_link(link, quote=True)
        if not title:
            return '<a href="%s" %s>%s</a>' % (link, text, self._link_rel(link))
        title = mistune.escape(title, quote=True)
        return '<a href="%s" title="%s" %s>%s</a>' % (link, title, text, self._link_rel(link))

    def block_code(self, code, lang):
        if not lang:
            return '\n<pre><code>%s</code></pre>\n' % mistune.escape(code).rstrip()
        return highlight_code(code, lang)

    def header(self, text, level, *args, **kwargs):
        return super(AwesomeRenderer, self).header(text, level + 2, *args, **kwargs)


def markdown(value, style):
    styles = getattr(settings, 'MARKDOWN_STYLES', {}).get(style, getattr(settings, 'MARKDOWN_DEFAULT_STYLE', {}))
    escape = styles.get('safe_mode', True)
    nofollow = styles.get('nofollow', True)

    renderer = AwesomeRenderer(escape=escape, nofollow=nofollow)
    markdown = mistune.Markdown(renderer=renderer, inline=CodeSafeInlineInlineLexer(renderer))
    return markdown(value)


@register.filter(name='markdown')
def markdown_filter(value, style):
    return mark_safe(markdown(value, style))
