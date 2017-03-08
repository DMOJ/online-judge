import logging
import re
from parser import ParserError
from urlparse import urlparse

import mistune
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from lxml import html
from lxml.etree import XMLSyntaxError

from judge.highlight_code import highlight_code
from judge.templatetags.markdown.camo import client as camo_client

register = template.Library()
logger = logging.getLogger('judge.html')

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
        self.nofollow = kwargs.pop('nofollow', True)
        self.lazyload = kwargs.pop('lazyload', False)
        self.use_camo = kwargs.pop('use_camo', False)
        super(AwesomeRenderer, self).__init__(*args, **kwargs)

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
        return '<a href="%s" %s>%s</a>' % (link, self._link_rel(link), text)

    def link(self, link, title, text):
        link = mistune.escape_link(link, quote=True)
        if not title:
            return '<a href="%s" %s>%s</a>' % (link, self._link_rel(link), text)
        title = mistune.escape(title, quote=True)
        return '<a href="%s" title="%s" %s>%s</a>' % (link, title, self._link_rel(link), text)

    def block_code(self, code, lang=None):
        if not lang:
            return '\n<pre><code>%s</code></pre>\n' % mistune.escape(code).rstrip()
        return highlight_code(code, lang)

    def header(self, text, level, *args, **kwargs):
        return super(AwesomeRenderer, self).header(text, level + 2, *args, **kwargs)


def markdown(value, style):
    styles = getattr(settings, 'MARKDOWN_STYLES', {}).get(style, getattr(settings, 'MARKDOWN_DEFAULT_STYLE', {}))
    escape = styles.get('safe_mode', True)
    nofollow = styles.get('nofollow', True)
    lazyload = styles.get('lazy_load', False)

    post_processors = []
    if styles.get('use_camo', False) and camo_client is not None:
        post_processors.append(camo_client.update_tree)

    renderer = AwesomeRenderer(escape=escape, nofollow=nofollow, lazyload=lazyload)
    markdown = mistune.Markdown(renderer=renderer, inline=CodeSafeInlineInlineLexer(renderer))
    result = markdown(value)

    if post_processors:
        try:
            tree = html.fromstring(result, parser=html.HTMLParser(recover=True))
        except (XMLSyntaxError, ParserError) as e:
            if str and (not isinstance(e, ParserError) or e.args[0] != 'Document is empty'):
                logger.exception('Failed to parse HTML string')
            tree = html.Element('div')
        for processor in post_processors:
            processor(tree)
        result = html.tostring(tree, encoding='unicode')
    return result


@register.filter(name='markdown')
def markdown_filter(value, style):
    return mark_safe(markdown(value, style))
