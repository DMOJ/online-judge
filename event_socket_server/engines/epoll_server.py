import errno
import select
import sys
from ..base_server import BaseServer
__author__ = 'Quantum'

if not hasattr(select, 'epoll'):
    raise ImportError('System does not support epoll')


class EpollServer(BaseServer):
    def __init__(self, *args, **kwargs):
        super(EpollServer, self).__init__(*args, **kwargs)
        self._epoll = select.epoll()
        self._fdmap = {}
        self._server_fd = self._server.fileno()

    def _register_write(self, client):
        self._epoll.modify(client.fileno(), select.EPOLLIN | select.EPOLLOUT | select.EPOLLERR | select.EPOLLHUP)

    def _register_read(self, client):
        self._epoll.modify(client.fileno(), select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP)

    def _clean_up_client(self, client, finalize=False):
        fd = client.fileno()
        try:
            self._epoll.unregister(fd)
        except IOError as e:
            if e.errno == errno.ENOENT:
                print>>sys.stderr, '(fd not registered: %d)' % fd
            else:
                raise
        del self._fdmap[fd]
        super(EpollServer, self)._clean_up_client(client, finalize)

    def _serve(self):
        self._server.listen(16)
        self._epoll.register(self._server_fd, select.EPOLLIN)
        try:
            while not self._stop.is_set():
                for fd, event in self._epoll.poll(self._dispatch_event()):
                    if fd == self._server_fd:
                        client = self._accept()
                        fd = client.fileno()
                        self._epoll.register(fd, select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP)
                        self._fdmap[fd] = client
                    elif event & (select.EPOLLHUP | select.EPOLLERR):
                        self._clean_up_client(self._fdmap[fd])
                    else:
                        if event & select.EPOLLIN:
                            self._nonblock_read(self._fdmap[fd])
                        if event & select.EPOLLOUT:
                            self._nonblock_write(self._fdmap[fd])
        finally:
            for client in self._clients:
                self._clean_up_client(client, True)
            self._epoll.unregister(self._server_fd)
            self._epoll.close()
            self._server.close()
