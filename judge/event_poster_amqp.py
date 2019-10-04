import json
import threading
from time import time

import pika
from django.conf import settings
from pika.exceptions import AMQPError

__all__ = ['EventPoster', 'post', 'last']


class EventPoster(object):
    def __init__(self):
        self._connect()
        self._exchange = settings.EVENT_DAEMON_AMQP_EXCHANGE

    def _connect(self):
        self._conn = pika.BlockingConnection(pika.URLParameters(settings.EVENT_DAEMON_AMQP))
        self._chan = self._conn.channel()

    def post(self, channel, message, tries=0):
        try:
            id = int(time() * 1000000)
            self._chan.basic_publish(self._exchange, '',
                                     json.dumps({'id': id, 'channel': channel, 'message': message}))
            return id
        except AMQPError:
            if tries > 10:
                raise
            self._connect()
            return self.post(channel, message, tries + 1)


_local = threading.local()


def _get_poster():
    if 'poster' not in _local.__dict__:
        _local.poster = EventPoster()
    return _local.poster


def post(channel, message):
    try:
        return _get_poster().post(channel, message)
    except AMQPError:
        try:
            del _local.poster
        except AttributeError:
            pass
    return 0


def last():
    return int(time() * 1000000)
