import httplib
import socket
import json
import logging
from urllib import urlencode

from django.conf import settings

logger = logging.getLogger(__name__)


class UHTTPConnection(httplib.HTTPConnection):
    """Subclass of Python library HTTPConnection that uses a unix-domain socket."""

    def __init__(self, path, **kwargs):
        httplib.HTTPConnection.__init__(self, 'localhost', **kwargs)
        self.path = path

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.path)
        self.sock = sock


def _get_connection(**kwargs):
    if settings.SIMPLE_COMET_IS_UNIX:
        return UHTTPConnection(settings.SIMPLE_COMET_ADDRESS, **kwargs)
    else:
        return httplib.HTTPConnection(settings.SIMPLE_COMET_ADDRESS, **kwargs)


def create_channel(name):
    conn = _get_connection()
    conn.request('POST', '/channels.json?' + urlencode({
        'channel_id': name,
    }))
    resp = conn.getresponse()
    if resp.status != 200:
        return False
    data = json.load(resp)
    logger.info('Comet: %s' % data)
    return data


def delete_channel(name):
    conn = _get_connection()
    conn.request('DELETE', '/channels/%s.json' % name)
    resp = conn.getresponse()
    if resp.status != 200:
        return False
    data = json.load(resp)
    logger.info('Comet: %s' % data)
    return data


def send_message(channel, message):
    conn = _get_connection()
    conn.request('POST', '/channels/%s.json?' % channel + urlencode({
        'content': message,
    }))
    resp = conn.getresponse()
    if resp.status != 200:
        return False
    data = json.load(resp)
    logger.info('Comet: %s' % data)
    return data


def get_message(channel):
    conn = _get_connection()
    conn.request('GET', '/channels/%s.json?' % channel)
    resp = conn.getresponse()
    if resp.status != 200:
        return []
    data = json.load(resp)
    logger.info('Comet: %s' % data)
    return data.get('messages', {}).get(channel, [])
