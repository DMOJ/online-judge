import logging
import socket
import threading
import time
from collections import defaultdict, deque
from functools import total_ordering
from heapq import heappop, heappush

logger = logging.getLogger('event_socket_server')


class SendMessage(object):
    __slots__ = ('data', 'callback')

    def __init__(self, data, callback):
        self.data = data
        self.callback = callback


@total_ordering
class ScheduledJob(object):
    __slots__ = ('time', 'func', 'args', 'kwargs', 'cancel', 'dispatched')

    def __init__(self, time, func, args, kwargs):
        self.time = time
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.cancel = False
        self.dispatched = False

    def __eq__(self, other):
        return self.time == other.time

    def __lt__(self, other):
        return self.time < other.time


class BaseServer(object):
    def __init__(self, addresses, client):
        self._servers = set()
        for address, port in addresses:
            info = socket.getaddrinfo(address, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for af, socktype, proto, canonname, sa in info:
                sock = socket.socket(af, socktype, proto)
                sock.setblocking(0)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(sa)
                self._servers.add(sock)

        self._stop = threading.Event()
        self._clients = set()
        self._ClientClass = client
        self._send_queue = defaultdict(deque)
        self._job_queue = []
        self._job_queue_lock = threading.Lock()

    def _serve(self):
        raise NotImplementedError()

    def _accept(self, sock):
        conn, address = sock.accept()
        conn.setblocking(0)
        client = self._ClientClass(self, conn)
        self._clients.add(client)
        return client

    def schedule(self, delay, func, *args, **kwargs):
        with self._job_queue_lock:
            job = ScheduledJob(time.time() + delay, func, args, kwargs)
            heappush(self._job_queue, job)
            return job

    def unschedule(self, job):
        with self._job_queue_lock:
            if job.dispatched or job.cancel:
                return False
            job.cancel = True
            return True

    def _register_write(self, client):
        raise NotImplementedError()

    def _register_read(self, client):
        raise NotImplementedError()

    def _clean_up_client(self, client, finalize=False):
        try:
            del self._send_queue[client.fileno()]
        except KeyError:
            pass
        client.on_close()
        client._socket.close()
        if not finalize:
            self._clients.remove(client)

    def _dispatch_event(self):
        t = time.time()
        tasks = []
        with self._job_queue_lock:
            while True:
                dt = self._job_queue[0].time - t if self._job_queue else 1
                if dt > 0:
                    break
                task = heappop(self._job_queue)
                task.dispatched = True
                if not task.cancel:
                    tasks.append(task)
        for task in tasks:
            logger.debug('Dispatching event: %r(*%r, **%r)', task.func, task.args, task.kwargs)
            task.func(*task.args, **task.kwargs)
        if not self._job_queue or dt > 1:
            dt = 1
        return dt

    def _nonblock_read(self, client):
        try:
            data = client._socket.recv(1024)
        except socket.error:
            self._clean_up_client(client)
        else:
            logger.debug('Read from %s: %d bytes', client.client_address, len(data))
            if not data:
                self._clean_up_client(client)
            else:
                try:
                    client._recv_data(data)
                except Exception:
                    logger.exception('Client recv_data failure')
                    self._clean_up_client(client)

    def _nonblock_write(self, client):
        fd = client.fileno()
        queue = self._send_queue[fd]
        try:
            top = queue[0]
            cb = client._socket.send(top.data)
            top.data = top.data[cb:]
            logger.debug('Send to %s: %d bytes', client.client_address, cb)
            if not top.data:
                logger.debug('Finished sending: %s', client.client_address)
                if top.callback is not None:
                    logger.debug('Calling callback: %s: %r', client.client_address, top.callback)
                    try:
                        top.callback()
                    except Exception:
                        logger.exception('Client write callback failure')
                        self._clean_up_client(client)
                        return
                queue.popleft()
                if not queue:
                    self._register_read(client)
                    del self._send_queue[fd]
        except socket.error:
            self._clean_up_client(client)

    def send(self, client, data, callback=None):
        logger.debug('Writing %d bytes to client %s, callback: %s', len(data), client.client_address, callback)
        self._send_queue[client.fileno()].append(SendMessage(data, callback))
        self._register_write(client)

    def stop(self):
        self._stop.set()

    def serve_forever(self):
        self._serve()

    def on_shutdown(self):
        pass
