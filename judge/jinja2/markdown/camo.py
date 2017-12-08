import hmac
from hashlib import sha1

from django import template
from django.conf import settings

register = template.Library()


class CamoClient(object):
    """Based on https://github.com/sionide21/camo-client"""

    def __init__(self, server, key, excluded=(), https=False):
        self.server = server.rstrip('/')
        self.key = key
        self.https = https
        self.excluded = excluded

    def image_url(self, url):
        return '%s/%s/%s' % (self.server,
                             hmac.new(self.key, url, sha1).hexdigest(),
                             url.encode('hex'))

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
            if img.get('src'):
                img.set('src', self.rewrite_url(img.get('src')))
        for obj in doc.xpath('.//object'):
            if obj.get('data'):
                obj.set('data', self.rewrite_url(obj.get('data')))


if getattr(settings, 'CAMO_URL', None) and getattr(settings, 'CAMO_KEY', None):
    client = CamoClient(settings.CAMO_URL, key=settings.CAMO_KEY,
                        excluded=getattr(settings, 'CAMO_EXCLUDE', ()),
                        https=getattr(settings, 'CAMO_HTTPS', False))
else:
    client = None
