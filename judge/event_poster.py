import threading
import json

from django.conf import settings
from websocket import create_connection, WebSocketConnectionClosedException

__all__ = ['EventPostingError', 'EventPoster', 'post', 'last']
_local = threading.local()


class EventPostingError(RuntimeError):
    pass


class EventPoster(object):
    def __init__(self):
        self._connect()

    def _connect(self):
        self._conn = create_connection(settings.EVENT_DAEMON_POST)
        if settings.EVENT_DAEMON_KEY is not None:
            self._conn.send(json.dumps({'command': 'auth', 'key': settings.EVENT_DAEMON_KEY}))
            resp = json.loads(self._conn.recv())
            if resp['status'] == 'error':
                raise EventPostingError(resp['code'])

    def post(self, channel, message):
        try:
            self._conn.send(json.dumps({'command': 'post', 'channel': channel, 'message': message}))
            resp = json.loads(self._conn.recv())
            if resp['status'] == 'error':
                raise EventPostingError(resp['code'])
            else:
                return resp['id']
        except WebSocketConnectionClosedException:
            self._connect()

    def last(self):
        try:
            self._conn.send('{"command": "last-msg"}')
            resp = json.loads(self._conn.recv())
            if resp['status'] == 'error':
                raise EventPostingError(resp['code'])
            else:
                return resp['id']
        except WebSocketConnectionClosedException:
            self._connect()


def _get_poster():
    if 'poster' not in _local.__dict__:
        _local.poster = EventPoster()
    return _local.poster


def post(channel, message):
    if settings.EVENT_DAEMON_USE:
        return _get_poster().post(channel, message)
    return 0


def last():
    if settings.EVENT_DAEMON_USE:
        return _get_poster().last()
    return 0