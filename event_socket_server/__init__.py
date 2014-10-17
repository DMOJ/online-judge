__author__ = 'Quantum'

from .base_server import BaseServer
from .handler import Handler
from .helpers import SizedPacketHandler, ZlibPacketHandler
from .engines import *


def get_preferred_engine(choices=('epoll', 'poll', 'select')):
    for choice in choices:
        if choice in engines:
            return engines[choice]
    return engines['select']