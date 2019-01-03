import hashlib
import json
import logging

import requests
from django.conf import settings
from django.core.cache import caches

from judge.utils.file_cache import HashFileCache
from judge.utils.unicode import utf8bytes

logger = logging.getLogger('judge.texoid')

TEXOID_ENABLED = hasattr(settings, 'TEXOID_URL')


class TexoidRenderer(object):
    def __init__(self):
        self.cache = HashFileCache(settings.TEXOID_CACHE_ROOT,
                                   settings.TEXOID_CACHE_URL,
                                   getattr(settings, 'TEXOID_GZIP', False))
        self.meta_cache = caches[getattr(settings, 'TEXOID_META_CACHE', 'default')]
        self.meta_cache_ttl = getattr(settings, 'TEXOID_META_CACHE_TTL', 86400)

    def query_texoid(self, document, hash):
        self.cache.create(hash)

        try:
            response = requests.post(settings.TEXOID_URL, body=utf8bytes(document), headers={
                'Content-Type': 'application/x-tex'
            })
            response.raise_for_status()
        except requests.HTTPError as e:
            if e.response.status == 400:
                logger.error('Texoid failed to render: %s\n%s', document, e.response.text)
            else:
                logger.exception('Failed to connect to texoid for: %s' % document)
            return
        except Exception:
            logger.exception('Failed to connect to texoid for: %s' % document)
            return

        try:
            data = response.json()
        except ValueError:
            logger.exception('Invalid texoid response for: %s\n%s', document, response.text)
            return

        if not data['success']:
            logger.error('Texoid failure for: %s\n%s', document, data)
            return {'error': data['error']}

        meta = data['meta']
        self.cache.cache_data(hash, 'meta', json.dumps(meta), url=False, gzip=False)

        result = {
            'png': self.cache.cache_data(hash, 'png', data['png'].decode('base64')),
            'svg': self.cache.cache_data(hash, 'svg', data['svg'].encode('utf-8')),
            'meta': meta,
        }
        return result

    def query_cache(self, hash):
        result = {
            'svg': self.cache.get_url(hash, 'svg'),
            'png': self.cache.get_url(hash, 'png'),
        }

        key = 'texoid:meta:' + hash
        cached_meta = self.meta_cache.get(key)
        if cached_meta is None:
            cached_meta = json.loads(self.cache.read_data(hash, 'meta').decode('utf-8'))
            self.meta_cache.set(key, cached_meta, self.meta_cache_ttl)
        result['meta'] = cached_meta

        return result

    def get_result(self, formula):
        hash = hashlib.sha1(formula).hexdigest()

        if self.cache.has_file(hash, 'svg'):
            return self.query_cache(hash)
        else:
            return self.query_texoid(formula, hash)
