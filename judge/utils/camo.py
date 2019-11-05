import hmac
from hashlib import sha1

from django.conf import settings

from judge.utils.unicode import utf8bytes


class CamoClient(object):
    """Based on https://github.com/sionide21/camo-client"""

    def __init__(self, server, key, excluded=(), https=False):
        self.server = server.rstrip('/')
        self.key = key
        self.https = https
        self.excluded = excluded

    def image_url(self, url):
        return '%s/%s/%s' % (self.server,
                             hmac.new(utf8bytes(self.key), utf8bytes(url), sha1).hexdigest(),
                             utf8bytes(url).hex())

    def rewrite_url(self, url):
        if url.startswith(self.server) or url.startswith(self.excluded):
            return url
        elif url.startswith(('http://', 'https://')):
            return self.image_url(url)
        elif url.startswith('//'):
            return self.rewrite_url(('https:' if self.https else 'http:') + url)
        else:
            return url

    def update_tree(self, doc):
        for img in doc.xpath('.//img'):
            for attr in ('src', 'data-src'):
                if img.get(attr):
                    img.set(attr, self.rewrite_url(img.get(attr)))
        for obj in doc.xpath('.//object'):
            if obj.get('data'):
                obj.set('data', self.rewrite_url(obj.get('data')))


if settings.DMOJ_CAMO_URL and settings.DMOJ_CAMO_KEY:
    client = CamoClient(settings.DMOJ_CAMO_URL, key=settings.DMOJ_CAMO_KEY,
                        excluded=settings.DMOJ_CAMO_EXCLUDE,
                        https=settings.DMOJ_CAMO_HTTPS)
else:
    client = None
