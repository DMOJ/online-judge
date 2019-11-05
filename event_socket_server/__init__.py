from .base_server import BaseServer
from .engines import *
from .handler import Handler
from .helpers import ProxyProtocolMixin, SizedPacketHandler, ZlibPacketHandler


def get_preferred_engine(choices=('epoll', 'poll', 'select')):
    for choice in choices:
        if choice in engines:
            return engines[choice]
    return engines['select']
