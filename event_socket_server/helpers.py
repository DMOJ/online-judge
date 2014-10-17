import struct
from .handler import Handler

__author__ = 'Quantum'
size_pack = struct.Struct('!I')


class SizedPacketHandler(Handler):
    def __init__(self, server, socket):
        super(SizedPacketHandler, self).__init__(server, socket)
        self._buffer = ''
        self._packetlen = 0

    def _packet(self, data):
        raise NotImplementedError()

    def _format_send(self, data):
        return data

    def _recv_data(self, data):
        self._buffer += data
        while len(self._buffer) >= self._packetlen if self._packetlen else len(self._buffer) >= size_pack.size:
            if self._packetlen:
                data = self._buffer[:self._packetlen]
                self._buffer = self._buffer[self._packetlen:]
                self._packetlen = 0
                self._packet(data)
            else:
                data = self._buffer[:size_pack.size]
                self._buffer = self._buffer[size_pack.size:]
                self._packetlen = size_pack.unpack(data)[0]

    def send(self, data, callback=None):
        data = self._format_send(data)
        self._send(size_pack.pack(len(data)) + data, callback)


class ZlibPacketHandler(SizedPacketHandler):
    def _format_send(self, data):
        return data.encode('zlib')

    def packet(self, data):
        raise NotImplementedError()

    def _packet(self, data):
        self.packet(data.decode('zlib'))
