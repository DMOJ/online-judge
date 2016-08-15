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

logger = logging.getLogger('judge.texoid')


def cache_data(hash, file, data, url=True):
    with open(os.path.join(settings.TEXOID_CACHE_ROOT, hash, file), 'wb') as f:
        f.write(data)
    if url:
        return urljoin(settings.TEXOID_CACHE_URL, '%s/%s' % (hash, file))


def query_mathoid(formula, hash):
    try:
        os.makedirs(os.path.join(settings.TEXOID_CACHE_ROOT, hash))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    try:
        request = urllib2.urlopen(settings.TEXOID_URL, urlencode({
            'q': formula
        }))
    except urllib2.HTTPError as e:
        if e.code == 400:
            logger.error('Texoid failed to render: %s\n%s', formula, e.read())
        logger.exception('Failed to connect to texoid for: %s' % formula)
        return
    except Exception:
        logger.exception('Failed to connect to texoid for: %s' % formula)
        return
    with closing(request) as f:
        data = f.read()
        try:
            data = json.loads(data)
        except ValueError:
            logger.exception('Invalid texoid response for: %s\n%s', formula, data)
            return

    if not data['success']:
        logger.error('Texoid failure for: %s\n%s', formula, data)
        return {'error': data['error']}

    result = {
        'png': cache_data(hash, 'png', data['png'].decode('base64')),
        'svg': cache_data(hash, 'svg', data['svg'].encode('utf-8')),
    }
    return result


def cache_complete(hash):
    return os.path.isfile(os.path.join(settings.TEXOID_CACHE_ROOT, hash, 'css'))


def query_cache(hash):
    result = {
        'svg': urljoin(settings.TEXOID_CACHE_URL, '%s/svg' % hash),
        'png': urljoin(settings.TEXOID_CACHE_URL, '%s/png' % hash),
    }
    return result


def get_result(formula):
    hash = hashlib.sha1(formula).hexdigest()
    if cache_complete(hash):
        result = query_cache(hash)
    else:
        result = query_mathoid(formula, hash)

    return result
