import errno
import logging
import select
import threading

from ..base_server import BaseServer

logger = logging.getLogger('event_socket_server')

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
        self._server_fds = {sock.fileno(): sock for sock in self._servers}
        self._close_lock = threading.RLock()

    def _register_write(self, client):
        logger.debug('On write mode: %s', client.client_address)
        self._poll.modify(client.fileno(), self.WRITE)

    def _register_read(self, client):
        logger.debug('On read mode: %s', client.client_address)
        self._poll.modify(client.fileno(), self.READ)

    def _clean_up_client(self, client, finalize=False):
        logger.debug('Taking close lock: cleanup')
        with self._close_lock:
            logger.debug('Cleaning up client: %s, finalize: %d', client.client_address, finalize)
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
        for fd, sock in self._server_fds.items():
            self._poll.register(fd, self.POLLIN)
            sock.listen(16)
        try:
            while not self._stop.is_set():
                for fd, event in self._poll.poll(self._dispatch_event()):
                    if fd in self._server_fds:
                        client = self._accept(self._server_fds[fd])
                        logger.debug('Accepting: %s', client.client_address)
                        fd = client.fileno()
                        self._poll.register(fd, self.READ)
                        self._fdmap[fd] = client
                    elif event & self.POLL_CLOSE:
                        logger.debug('Client closed: %s', self._fdmap[fd].client_address)
                        self._clean_up_client(self._fdmap[fd])
                    else:
                        logger.debug('Taking close lock: event loop')
                        with self._close_lock:
                            try:
                                client = self._fdmap[fd]
                            except KeyError:
                                pass
                            else:
                                logger.debug('Client active: %s, read: %d, write: %d',
                                             client.client_address,
                                             event & self.POLLIN,
                                             event & self.POLLOUT)
                                if event & self.POLLIN:
                                    logger.debug('Non-blocking read on client: %s', client.client_address)
                                    self._nonblock_read(client)
                                # Might be closed in the read handler.
                                if event & self.POLLOUT and fd in self._fdmap:
                                    logger.debug('Non-blocking write on client: %s', client.client_address)
                                    self._nonblock_write(client)
        finally:
            logger.info('Shutting down server')
            self.on_shutdown()
            for client in self._clients:
                self._clean_up_client(client, True)
            for fd, sock in self._server_fds.items():
                self._poll.unregister(fd)
                sock.close()
            if self.NEED_CLOSE:
                self._poll.close()
