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
        self.nofollow = kwargs.pop('nofollow', True)
        self.lazyload = kwargs.pop('lazyload', False)
        super(AwesomeRenderer, self).__init__(*args, **kwargs)

    def image(self, src, title, text):
        if camo_client:
            src = camo_client.image_url(src)

        src = mistune.escape_link(src, quote=True)
        text = mistune.escape(text, quote=True)
        if title:
            title = mistune.escape(title, quote=True)
            html = '<img src="%s" alt="%s" title="%s"' % (src, text, title)
        else:
            html = '<img src="%s" alt="%s"' % (src, text)
        if self.options.get('use_xhtml'):
            return '%s />' % html
        return '%s>' % html

    # @register.filter(is_safe=True)
    # def lazy_load(text):
    #     blank = static('blank.gif')
    #     tree = lxml_tree.fromstring(text)
    #     for img in tree.xpath('.//img'):
    #         src = img.get('src')
    #         if src.startswith('data'):
    #             continue
    #         noscript = html.Element('noscript')
    #         noscript.append(deepcopy(img))
    #         img.addprevious(noscript)
    #         img.set('data-src', src)
    #         img.set('src', blank)
    #         img.set('class', img.get('class') + ' unveil' if img.get('class') else 'unveil')
    #     return tree

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
    lazyload = styles.get('lazy_load', False)

    renderer = AwesomeRenderer(escape=escape, nofollow=nofollow, lazyload=lazyload)
    markdown = mistune.Markdown(renderer=renderer, inline=CodeSafeInlineInlineLexer(renderer))
    return markdown(value)


@register.filter(name='markdown')
def markdown_filter(value, style):
    return mark_safe(markdown(value, style))
