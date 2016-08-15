import errno
import hashlib
import json
import logging
import os
import urllib2
from contextlib import closing
from urllib import urlencode
from urlparse import urljoin

from django.conf import settings
from django.core.cache import caches
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from judge.math_parser import MathHTMLParser

logger = logging.getLogger('judge.mathoid')


class MathoidMathParser(MathHTMLParser):
    def __init__(self, type=None):
        MathHTMLParser.__init__(self)

        type = type or getattr(settings, 'MATHOID_DEFAULT_TYPE', 'jax')
        assert type in ('svg', 'mml', 'tex', 'jax')
        self.type = type.rstrip('+')
        self.use_jax = type.endswith('+')

        self.mathoid_url = settings.MATHOID_URL
        self.cache_dir = settings.MATHOID_CACHE_ROOT
        self.cache_url = settings.MATHOID_CACHE_URL
        self.gzip_cache = getattr(settings, 'MATHOID_GZIP', False)

        mml_cache = getattr(settings, 'MATHOID_MML_CACHE', None)
        self.mml_cache = mml_cache and caches[mml_cache]
        self.css_cache = caches[getattr(settings, 'MATHOID_CSS_CACHE', 'default')]

        self.mml_cache_ttl = getattr(settings, 'MATHOID_MML_CACHE_TTL', 86400)

    def cache_complete(self, hash):
        return os.path.isfile(os.path.join(self.cache_dir, hash, 'css'))

    def cache_data(self, hash, file, data, url=True, gz=False):
        with open(os.path.join(self.cache_dir, hash, file), 'wb') as f:
            f.write(data)
        if url:
            return urljoin(self.cache_url, '%s/%s' % (hash, file))

    def query_mathoid(self, formula, hash):
        try:
            os.makedirs(os.path.join(self.cache_dir, hash))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        try:
            request = urllib2.urlopen(self.mathoid_url, urlencode({
                'q': formula, 'type': 'tex' if formula.startswith('\displaystyle') else 'inline-tex'
            }))
        except urllib2.HTTPError as e:
            if e.code == 400:
                logger.error('Mathoid failed to render: %s\n%s', formula, e.read())
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
            'png': self.cache_data(hash, 'png', bytearray(data['png']['data'])),
            'svg': self.cache_data(hash, 'svg', data['svg'].encode('utf-8')),
        }
        self.cache_data(hash, 'mml', mml.encode('utf-8'), url=False)
        self.cache_data(hash, 'css', css.encode('utf-8'), url=False)
        return result

    def query_cache(self, hash):
        result = {
            'svg': urljoin(self.cache_url, '%s/svg' % hash),
            'png': urljoin(self.cache_url, '%s/png' % hash),
        }

        key = 'mathoid:css:' + hash
        css = result['css'] = self.css_cache.get(key)
        if css is None:
            with open(os.path.join(self.cache_dir, hash, 'css'), 'rb') as f:
                css = result['css'] = f.read().decode('utf-8')
                self.css_cache.set(key, css, self.mml_cache_ttl)

        mml = None
        if self.mml_cache:
            mml = result['mml'] = self.mml_cache.get('mathoid:mml:' + hash)
        if mml is None:
            with open(os.path.join(self.cache_dir, hash, 'mml'), 'rb') as f:
                mml = result['mml'] = f.read().decode('utf-8')
            if self.mml_cache:
                self.mml_cache.set('mathoid:mml:' + hash, mml, self.mml_cache_ttl)
        return result

    def get_result(self, formula):
        if self.type == 'tex':
            return

        hash = hashlib.sha1(formula).hexdigest()
        if self.cache_complete(hash):
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
        }[self.type](result)

    def output_mml(self, result):
        return result['mml']

    def output_msp(self, result):
        # 100% MediaWiki compatibility.
        return format_html(u'<span class="{5}-math">'
                           u'<span class="mwe-math-mathml-{5} mwe-math-mathml-a11y"'
                           u' style="display: none;">{0}</span>'
                           u'<img src="{1}" class="mwe-math-fallback-image-{5}" onerror="this.src=\'{2}\'"'
                           u' aria-hidden="true" style="{3}" alt="{4}"></span>',
                           mark_safe(result['mml']), result['svg'], result['png'], result['css'], result['tex'],
                           ['inline', 'display'][result['display']])

    def output_jax(self, result):
        return format_html(u'<span class="{4}">'
                           u'''<img class="tex-image" src="{0}" style="{2}" alt="{3}" onerror="this.src='{1}'">'''
                           u'''<span class="tex-text" style="display:none">{5}{3}{5}</span>'''
                           u'</span>',
                           result['svg'], result['png'], result['css'], result['tex'],
                           ['inline-math', 'display-math'][result['display']], ['~', '$$'][result['display']])

    def output_svg(self, result):
        return format_html(u'''<img class="{4}" src="{0}" style="{2}" alt="{3}" onerror="this.src='{1}'">''',
                           result['svg'], result['png'], result['css'], result['tex'],
                           ['inline-math', 'display-math'][result['display']])

    def display_math(self, math):
        return self.get_result('\displaystyle ' + math) or '$$%s$$' % math

    def inline_math(self, math):
        return self.get_result(math) or '~%s~' % math
