import errno
import select
import socket
import sys
import threading
from ..base_server import BaseServer
__author__ = 'Quantum'

if not hasattr(select, 'poll'):
    raise ImportError('System does not support poll')


class PollServer(BaseServer):
    poll = select.poll
    WRITE = select.POLLIN | select.POLLOUT | select.POLLERR | select.POLLHUP
    READ = select.POLLIN | select.POLLERR | select.POLLHUP
    POLLIN = select.POLLIN
    POLLOUT = select.POLLOUT
    POLL_CLOSE = select.POLLERR | select.POLLHUP
    NEED_CLOSE = False

    def __init__(self, *args, **kwargs):
        super(PollServer, self).__init__(*args, **kwargs)
        self._poll = self.poll()
        self._fdmap = {}
        self._server_fd = self._server.fileno()
        self._close_lock = threading.RLock()

    def _register_write(self, client):
        self._poll.modify(client.fileno(), self.WRITE)

    def _register_read(self, client):
        self._poll.modify(client.fileno(), self.READ)

    def _clean_up_client(self, client, finalize=False):
        with self._close_lock:
            fd = client.fileno()
            try:
                self._poll.unregister(fd)
            except IOError as e:
                if e.errno != errno.ENOENT:
                    raise
            except KeyError:
                pass
            del self._fdmap[fd]
            super(PollServer, self)._clean_up_client(client, finalize)

    def _serve(self):
        self._server.listen(16)
        self._poll.register(self._server_fd, self.POLLIN)
        try:
            while not self._stop.is_set():
                for fd, event in self._poll.poll(self._dispatch_event()):
                    if fd == self._server_fd:
                        client = self._accept()
                        fd = client.fileno()
                        self._poll.register(fd, self.READ)
                        self._fdmap[fd] = client
                    elif event & self.POLL_CLOSE:
                        self._clean_up_client(self._fdmap[fd])
                    else:
                        with self._close_lock:
                            try:
                                client = self._fdmap[fd]
                            except KeyError:
                                pass
                            else:
                                if event & self.POLLIN:
                                    self._nonblock_read(client)
                                # Might be closed in the read handler.
                                if event & self.POLLOUT and fd in self._fdmap:
                                    self._nonblock_write(client)
        finally:
            for client in self._clients:
                self._clean_up_client(client, True)
            self._poll.unregister(self._server_fd)
            if self.NEED_CLOSE:
                self._poll.close()
            self._server.close()
