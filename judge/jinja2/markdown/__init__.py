import logging
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import mistune
from bleach.sanitizer import Cleaner
from django.conf import settings
from jinja2 import Markup
from lxml import html
from lxml.etree import ParserError, XMLSyntaxError

from judge.highlight_code import highlight_code
from judge.jinja2.markdown.lazy_load import lazy_load as lazy_load_processor
from judge.jinja2.markdown.math import MathInlineGrammar, MathInlineLexer, MathRenderer
from judge.utils.camo import client as camo_client
from judge.utils.texoid import TEXOID_ENABLED, TexoidRenderer
from .bleach_whitelist import all_styles, mathml_attrs, mathml_tags
from .. import registry

logger = logging.getLogger('judge.html')

NOFOLLOW_WHITELIST = settings.NOFOLLOW_EXCLUDED


class CodeSafeInlineGrammar(mistune.InlineGrammar):
    double_emphasis = re.compile(r'^\*{2}([\s\S]+?)()\*{2}(?!\*)')  # **word**
    emphasis = re.compile(r'^\*((?:\*\*|[^\*])+?)()\*(?!\*)')  # *word*


class AwesomeInlineGrammar(MathInlineGrammar, CodeSafeInlineGrammar):
    pass


class AwesomeInlineLexer(MathInlineLexer, mistune.InlineLexer):
    grammar_class = AwesomeInlineGrammar


class AwesomeRenderer(MathRenderer, mistune.Renderer):
    def __init__(self, *args, **kwargs):
        self.nofollow = kwargs.pop('nofollow', True)
        self.texoid = TexoidRenderer() if kwargs.pop('texoid', False) else None
        self.parser = HTMLParser()
        super(AwesomeRenderer, self).__init__(*args, **kwargs)

    def _link_rel(self, href):
        if href:
            try:
                url = urlparse(href)
            except ValueError:
                return ' rel="nofollow"'
            else:
                if url.netloc and url.netloc not in NOFOLLOW_WHITELIST:
                    return ' rel="nofollow"'
        return ''

    def autolink(self, link, is_email=False):
        text = link = mistune.escape(link)
        if is_email:
            link = 'mailto:%s' % link
        return '<a href="%s"%s>%s</a>' % (link, self._link_rel(link), text)

    def table(self, header, body):
        return (
            '<table class="table">\n<thead>%s</thead>\n'
            '<tbody>\n%s</tbody>\n</table>\n'
        ) % (header, body)

    def link(self, link, title, text):
        link = mistune.escape_link(link)
        if not title:
            return '<a href="%s"%s>%s</a>' % (link, self._link_rel(link), text)
        title = mistune.escape(title, quote=True)
        return '<a href="%s" title="%s"%s>%s</a>' % (link, title, self._link_rel(link), text)

    def block_code(self, code, lang=None):
        if not lang:
            return '\n<pre><code>%s</code></pre>\n' % mistune.escape(code).rstrip()
        return highlight_code(code, lang)

    def block_html(self, html):
        if self.texoid and html.startswith('<latex'):
            attr = html[6:html.index('>')]
            latex = html[html.index('>') + 1:html.rindex('<')]
            latex = self.parser.unescape(latex)
            result = self.texoid.get_result(latex)
            if not result:
                return '<pre>%s</pre>' % mistune.escape(latex, smart_amp=False)
            elif 'error' not in result:
                img = ('''<img src="%(svg)s" onerror="this.src='%(png)s';this.onerror=null"'''
                       'width="%(width)s" height="%(height)s"%(tail)s>') % {
                    'svg': result['svg'], 'png': result['png'],
                    'width': result['meta']['width'], 'height': result['meta']['height'],
                    'tail': ' /' if self.options.get('use_xhtml') else '',
                }
                style = ['max-width: 100%',
                         'height: %s' % result['meta']['height'],
                         'max-height: %s' % result['meta']['height'],
                         'width: %s' % result['meta']['height']]
                if 'inline' in attr:
                    tag = 'span'
                else:
                    tag = 'div'
                    style += ['text-align: center']
                return '<%s style="%s">%s</%s>' % (tag, ';'.join(style), img, tag)
            else:
                return '<pre>%s</pre>' % mistune.escape(result['error'], smart_amp=False)
        return super(AwesomeRenderer, self).block_html(html)

    def header(self, text, level, *args, **kwargs):
        return super(AwesomeRenderer, self).header(text, level + 2, *args, **kwargs)


cleaner_cache = {}


def get_cleaner(name, params):
    if name in cleaner_cache:
        return cleaner_cache[name]

    if params.get('styles') is True:
        params['styles'] = all_styles

    if params.pop('mathml', False):
        params['tags'] = params.get('tags', []) + mathml_tags
        params['attributes'] = params.get('attributes', {}).copy()
        params['attributes'].update(mathml_attrs)

    cleaner = cleaner_cache[name] = Cleaner(**params)
    return cleaner


@registry.filter
def markdown(value, style, math_engine=None, lazy_load=False):
    styles = settings.MARKDOWN_STYLES.get(style, settings.MARKDOWN_DEFAULT_STYLE)
    escape = styles.get('safe_mode', True)
    nofollow = styles.get('nofollow', True)
    texoid = TEXOID_ENABLED and styles.get('texoid', False)
    math = getattr(settings, 'MATHOID_URL') and styles.get('math', False)
    bleach_params = styles.get('bleach', {})

    post_processors = []
    if styles.get('use_camo', False) and camo_client is not None:
        post_processors.append(camo_client.update_tree)
    if lazy_load:
        post_processors.append(lazy_load_processor)

    renderer = AwesomeRenderer(escape=escape, nofollow=nofollow, texoid=texoid,
                               math=math and math_engine is not None, math_engine=math_engine)
    markdown = mistune.Markdown(renderer=renderer, inline=AwesomeInlineLexer,
                                parse_block_html=1, parse_inline_html=1)
    result = markdown(value)

    if post_processors:
        tree = html.Element('div')
        try:
            tree.extend(html.fragments_fromstring(result, parser=html.HTMLParser(recover=True)))
        except (XMLSyntaxError, ParserError) as e:
            if result and (not isinstance(e, ParserError) or e.args[0] != 'Document is empty'):
                logger.exception('Failed to parse HTML string')
        for processor in post_processors:
            processor(tree)
        result = html.tostring(tree, encoding='unicode')[len('<div>'):-len('</div>')]
    if bleach_params:
        result = get_cleaner(style, bleach_params).clean(result)
    return Markup(result)
