import errno
import hashlib
import json
import os
import urllib2
from contextlib import closing
from urllib import quote
from urlparse import urljoin

from django.conf import settings
from django.core.cache import caches
from django.utils.html import format_html

from judge.math_parser import MathHTMLParser


class MathoidMathParser(MathHTMLParser):
    def __init__(self, type=None):
        assert type in ('svg', 'mml', 'tex', 'png')
        MathHTMLParser.__init__(self)

        self.type = type or getattr(settings, 'MATHOID_DEFAULT_TYPE', 'svg')
        self.mathoid_url = settings.MATHOID_URL
        self.cache_dir = settings.MATHOID_CACHE_ROOT
        self.cache_url = settings.MATHOID_CACHE_URL
        self.mathid_types = getattr(settings, 'MATHOID_TYPES', ('png', 'svg', 'mml'))

        mml_cache = getattr(settings, 'MATHOID_MML_CACHE', None)
        self.mml_cache = mml_cache and caches[mml_cache]
        self.css_cache = caches[getattr(settings, 'MATHOID_CSS_CACHE', 'default')]

        self.mml_cache_ttl = getattr(settings, 'MATHOID_MML_CACHE_TTL', 86400)

    def cache_complete(self, hash):
        return os.path.isfile(os.path.join(self.cache_dir, hash, 'css'))

    def cache_data(self, hash, file, data, url=True):
        with open(os.path.join(self.cache_dir, hash, file), 'wb') as f:
            f.write(data)
        if url:
            return urljoin(self.cache_url, hash, file)

    def query_mathoid(self, formula, hash):
        try:
            os.makedirs(os.path.join(self.cache_dir, hash))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        with closing(urllib2.urlopen(self.mathoid_url, 'q=' + quote(formula))) as f:
            data = json.load(f)
        result = {}
        if not data['success'] or 'mathoidStyle' not in result:
            return
        css = result['css'] = data['mathoidStyle']
        if 'png' in self.mathid_types and 'png' in data:
            result['png'] = self.cache_data(hash, 'png', bytearray(data['png']['data']))
        else:
            result['png'] = None
        if 'svg' in self.mathid_types and 'svg' in data:
            result['svg'] = self.cache_data(hash, 'png', data['svg'])
        else:
            result['svg'] = None
        if 'mml' in self.mathid_types and 'mml' in data:
            result['mml'] = data['mml']
            self.cache_data(hash, 'mml', data['mml'], url=False)
        else:
            result['mml'] = data['mml']
        self.cache_data(hash, 'css', css, url=False)
        return result

    def query_cache(self, hash, type):
        result = {}
        if type in ('svg', 'png'):
            result[type] = urljoin(self.cache_url, hash, type)

            key = 'mathoid:css:' + hash
            css = result['css'] = self.css_cache.get(key)
            if css is None:
                with open(os.path.join(self.cache_dir, hash, 'css')) as f:
                    css = result['css'] = f.read()
                    self.mml_cache.set(key, css, self.mml_cache_ttl)
        elif type == 'mml':
            mml = None
            if self.mml_cache:
                mml = result['mml'] = self.mml_cache.get('mathoid:mml:' + hash)
            if mml is None:
                with open(os.path.join(self.cache_dir, hash, 'mml')) as f:
                    mml = result['mml'] = f.read()
                if self.mml_cache:
                    self.mml_cache.set('mathoid:mml:' + hash, mml, self.mml_cache_ttl)
        return result

    def get_result(self, formula):
        hash = hashlib.sha1(formula).hexdigest()
        if self.cache_complete(hash):
            result = self.query_cache(hash, self.type)
        else:
            result = self.query_mathoid(formula, hash)

        if not result.get(self.type):
            return None

        return {
            'mml': self.output_mml,
            'svg': self.output_svg,
            'png': self.output_png,
        }[self.type](result)

    def output_mml(self, result):
        return result['mml']

    def output_image(self, result, type):
        return format_html('<img src="{0}" style="{1}>', result[type], result['css'])

    def output_svg(self, result):
        return self.output_image(result, 'svg')

    def output_png(self, result):
        return self.output_image(result, 'png')

    def display_math(self, math):
        return self.get_result('\displaystyle ' + math) or '$$%s$$' % math

    def inline_math(self, math):
        return self.get_result(math) or '~%s~' % math
