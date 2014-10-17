import select

__author__ = 'Quantum'
engines = {}

from .select_server import SelectServer
engines['select'] = SelectServer

if hasattr(select, 'epoll'):
    from .epoll_server import EpollServer
    engines['epoll'] = EpollServer

del select