import select

__author__ = 'Quantum'
engines = {}

from .select_server import SelectServer
engines['select'] = SelectServer

if hasattr(select, 'poll'):
    from .poll_server import PollServer
    engines['poll'] = PollServer

if hasattr(select, 'epoll'):
    from .epoll_server import EpollServer
    engines['epoll'] = EpollServer

del select