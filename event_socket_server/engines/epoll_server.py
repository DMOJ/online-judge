import select
__author__ = 'Quantum'

if not hasattr(select, 'epoll'):
    raise ImportError('System does not support epoll')
from .poll_server import PollServer


class EpollServer(PollServer):
    poll = select.epoll
    WRITE = select.EPOLLIN | select.EPOLLOUT | select.EPOLLERR | select.EPOLLHUP
    READ = select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP
    POLLIN = select.EPOLLIN
    POLLOUT = select.EPOLLOUT
    POLL_CLOSE = select.EPOLLHUP | select.EPOLLERR
    NEED_CLOSE = True
