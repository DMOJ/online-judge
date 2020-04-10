import socketserver
import threading


class Handler(object):
    def __init__(self, server, socket):
        self._socket = socket
        self.server = server
        self.client_address = socket.getpeername()

    def fileno(self):
        return self._socket.fileno()

    def _recv_data(self, data):
        raise NotImplementedError

    def _send(self, data, callback=None):
        return self.server.send(self, data, callback)

    def close(self):
        self.server._clean_up_client(self)

    def on_close(self):
        pass

    @property
    def socket(self):
        return self._socket


class FakeServer:
    def __init__(self, handler, socket):
        self.handler = handler
        self.socket = socket
        self.timers = set()

    def send(self, _, data, callback):
        self.socket.sendall(data)
        if callback:
            callback()

    def _clean_up_client(self, client):
        self.handler.running = False
        client.on_close()

    def schedule(self, time, callback):
        def timer_func():
            callback()
            self.timers.discard(timer)

        timer = threading.Timer(time, timer_func)
        self.timers.add(timer)
        timer.start()
        return timer

    def unschedule(self, timer):
        timer.cancel()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        for timer in self.timers:
            timer.cancel()


class TCPHandler(socketserver.BaseRequestHandler):
    client = None
    buffer_size = 4096
    running = True

    @classmethod
    def wrap(cls, client):
        return type('TCPHandler', (cls,), {'client': client})

    def handle(self):
        with FakeServer(self, self.request) as server:
            handler = self.client(server, self.request)

            while self.running:
                received = self.request.recv(self.buffer_size)
                if not received:
                    return
                handler._recv_data(received)
