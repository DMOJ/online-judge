import hashlib
import json
import logging
import re
import urllib2
from contextlib import closing
from urllib import urlencode

from django.conf import settings
from django.core.cache import caches
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from mistune import escape

from judge.utils.file_cache import HashFileCache

logger = logging.getLogger('judge.mathoid')
reescape = re.compile(r'(?<!\\)(?:\\{2})*[$]')

REPLACES = [
    (u'\u2264', r'\le'),
    (u'\u2265', r'\ge'),
    (u'\u2026', '...'),
    (u'\u2212', '-'),
    ('&le;', r'\le'),
    ('&ge;', r'\ge'),
    ('&lt;', '<'),
    ('&gt;', '>'),
    ('&amp;', '&'),
    ('&#8722;', '-'),
    ('&#8804;', r'\le'),
    ('&#8805;', r'\ge'),
    ('&#8230;', '...'),
    (r'\lt', '<'),
    (r'\gt', '>'),
]


def format_math(math):
    for a, b in REPLACES:
        math = math.replace(a, b)
    return math


class MathoidMathParser(object):
    types = ('svg', 'mml', 'tex', 'jax')

    def __init__(self, type):
        self.type = type

        self.mathoid_url = settings.MATHOID_URL
        self.cache = HashFileCache(settings.MATHOID_CACHE_ROOT,
                                   settings.MATHOID_CACHE_URL,
                                   getattr(settings, 'MATHOID_GZIP', False))

        mml_cache = getattr(settings, 'MATHOID_MML_CACHE', None)
        self.mml_cache = mml_cache and caches[mml_cache]
        self.css_cache = caches[getattr(settings, 'MATHOID_CSS_CACHE', 'default')]

        self.mml_cache_ttl = getattr(settings, 'MATHOID_MML_CACHE_TTL', 86400)

    def query_mathoid(self, formula, hash):
        self.cache.create(hash)

        try:
            request = urllib2.urlopen(self.mathoid_url, urlencode({
                'q': reescape.sub(lambda m: '\\' + m.group(0), formula).encode('utf-8'),
                'type': 'tex' if formula.startswith('\displaystyle') else 'inline-tex'
            }))
        except urllib2.HTTPError as e:
            if e.code == 400:
                logger.error('Mathoid failed to render: %s\n%s', formula, e.read())
            else:
                logger.exception('Failed to connect to mathoid for: %s' % formula)
            return
        except Exception:
            logger.exception('Failed to connect to mathoid for: %s' % formula)
            return

        with closing(request) as f:
            data = f.read()
            try:
                data = json.loads(data)
            except ValueError:
                logger.exception('Invalid mathoid response for: %s\n%s', formula, data)
                return

        if not data['success']:
            logger.error('Mathoid failure for: %s\n%s', formula, data)
            return

        if any(i not in data for i in ('mml', 'png', 'svg', 'mathoidStyle')):
            logger.error('Mathoid did not return required information (mml, png, svg, mathoidStyle needed):\n%s', data)
            return

        css = data['mathoidStyle']
        mml = data['mml']
        result = {
            'css': css, 'mml': mml,
            'png': self.cache.cache_data(hash, 'png', bytearray(data['png']['data'])),
            'svg': self.cache.cache_data(hash, 'svg', data['svg'].encode('utf-8')),
        }
        self.cache.cache_data(hash, 'mml', mml.encode('utf-8'), url=False, gzip=False)
        self.cache.cache_data(hash, 'css', css.encode('utf-8'), url=False, gzip=False)
        return result

    def query_cache(self, hash):
        result = {
            'svg': self.cache.get_url(hash, 'svg'),
            'png': self.cache.get_url(hash, 'png'),
        }

        key = 'mathoid:css:' + hash
        css = result['css'] = self.css_cache.get(key)
        if css is None:
            css = result['css'] = self.cache.read_data(hash, 'css').decode('utf-8')
            self.css_cache.set(key, css, self.mml_cache_ttl)

        mml = None
        if self.mml_cache:
            mml = result['mml'] = self.mml_cache.get('mathoid:mml:' + hash)
        if mml is None:
            mml = result['mml'] = self.cache.read_data(hash, 'mml').decode('utf-8')
            if self.mml_cache:
                self.mml_cache.set('mathoid:mml:' + hash, mml, self.mml_cache_ttl)
        return result

    def get_result(self, formula):
        if self.type == 'tex':
            return

        if isinstance(formula, unicode):
            hash = hashlib.sha1(formula.encode('utf-8')).hexdigest()
        else:
            hash = hashlib.sha1(formula).hexdigest()
            formula = formula.decode('utf-8')
        if self.cache.has_file(hash, 'css'):
            result = self.query_cache(hash)
        else:
            result = self.query_mathoid(formula, hash)

        if not result:
            return None

        result['tex'] = formula
        result['display'] = formula.startswith('\displaystyle')
        return {
            'mml': self.output_mml,
            'msp': self.output_msp,
            'svg': self.output_svg,
            'jax': self.output_jax,
            'png': self.output_png,
            'raw': lambda x: x,
        }[self.type](result)

    def output_mml(self, result):
        return result['mml']

    def output_msp(self, result):
        # 100% MediaWiki compatibility.
        return format_html(u'<span class="{5}-math">'
                           u'<span class="mwe-math-mathml-{5} mwe-math-mathml-a11y"'
                           u' style="display: none;">{0}</span>'
                           u'<img src="{1}" class="mwe-math-fallback-image-{5}"'
                           u' onerror="this.src=\'{2}\';this.onerror=null"'
                           u' aria-hidden="true" style="{3}" alt="{4}"></span>',
                           mark_safe(result['mml']), result['svg'], result['png'], result['css'], result['tex'],
                           ['inline', 'display'][result['display']])

    def output_jax(self, result):
        return format_html(u'<span class="{4}">'
                           u'''<img class="tex-image" src="{0}" style="{2}" alt="{3}"'''
                           u''' onerror="this.src='{1}';this.onerror=null">'''
                           u'''<span class="tex-text" style="display:none">{5}{3}{5}</span>'''
                           u'</span>',
                           result['svg'], result['png'], result['css'], result['tex'],
                           ['inline-math', 'display-math'][result['display']], ['~', '$$'][result['display']])

    def output_svg(self, result):
        return format_html(u'<img class="{4}" src="{0}" style="{2}" alt="{3}" '
                           u'''onerror="this.src='{1}';this.onerror=null">''',
                           result['svg'], result['png'], result['css'], result['tex'],
                           ['inline-math', 'display-math'][result['display']])

    def output_png(self, result):
        return format_html(u'<img class="{3}" src="{0}" style="{1}" alt="{2}">',
                           result['png'], result['css'], result['tex'],
                           ['inline-math', 'display-math'][result['display']])

    def display_math(self, math):
        math = format_math(math)
        return self.get_result('\displaystyle ' + math) or r'\[%s\]' % escape(math)

    def inline_math(self, math):
        math = format_math(math)
        return self.get_result(math) or r'\(%s\)' % escape(math)
