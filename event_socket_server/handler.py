__author__ = 'Quantum'


class Handler(object):
    def __init__(self, server, socket):
        self._socket = socket
        self.server = server

    def fileno(self):
        return self._socket.fileno()

    def _recv_data(self, data):
        raise NotImplementedError

    def _send(self, data):
        return self.server.send(self, data)

    def close(self):
        self.server._clean_up_client(self)

    def on_close(self):
        pass

    @property
    def socket(self):
        return self._socket