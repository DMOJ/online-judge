import logging
import socket
import struct
import zlib
from itertools import chain
from socketserver import BaseRequestHandler

from netaddr import IPGlob, IPSet

from judge.utils.unicode import utf8text

logger = logging.getLogger('judge.bridge')

size_pack = struct.Struct('!I')
assert size_pack.size == 4


def proxy_list(human_readable):
    globs = []
    addrs = []
    for item in human_readable:
        if '*' in item or '-' in item:
            globs.append(IPGlob(item))
        else:
            addrs.append(item)
    return IPSet(chain(chain.from_iterable(globs), addrs))


class Disconnect(Exception):
    pass


class ZlibPacketHandler(BaseRequestHandler):
    proxies = []

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self.server_address = server.server_address

    @property
    def timeout(self):
        return self.request.gettimeout()

    @timeout.setter
    def timeout(self, timeout):
        self.request.settimeout(timeout or None)

    def read_sized_packet(self, size, initial=None):
        buffer = []
        remainder = size

        if initial:
            buffer.append(initial)
            remainder -= len(initial)

        while remainder:
            data = self.request.recv(remainder)
            remainder -= len(data)
            buffer.append(data)
        self._packet(b''.join(buffer))

    def parse_proxy_protocol(self, line):
        if len(line) < 2:
            raise Disconnect()

        if line[1] == b'TCP4':
            if len(line) != 6:
                raise Disconnect()
            self.client_address = (utf8text(line[2]), utf8text(line[4]))
            self.server_address = (utf8text(line[3]), utf8text(line[5]))
        elif line[1] == b'TCP6':
            self.client_address = (utf8text(line[2]), utf8text(line[4]), 0, 0)
            self.server_address = (utf8text(line[3]), utf8text(line[5]), 0, 0)
        elif line[1] != b'UNKNOWN':
            raise Disconnect()

    def read_size(self, buffer=b''):
        while len(buffer) < size_pack.size:
            recv = self.request.recv(size_pack.size - len(buffer))
            if not recv:
                raise Disconnect()
            buffer += recv
        return size_pack.unpack(buffer)[0]

    def _packet(self, data):
        self.packet(zlib.decompress(data).decode('utf-8'))

    def packet(self, data):
        raise NotImplementedError()

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_invalid(self):
        raise ValueError()

    def on_timeout(self):
        raise Disconnect()

    def handle(self):
        self.on_connect()

        try:
            tag = self.request.recv(4)
            if self.client_address[0] in self.proxies and tag == b'PROX':
                # Max line length for PROXY protocol is 107, and we received 4 already.
                line = tag + self.request.recv(103)
                proxy, newline, remainder = line.partition(b'\r\n')
                if not newline:
                    raise Disconnect()
                self.parse_proxy_protocol(proxy)

                while remainder:
                    while len(remainder) < size_pack.size:
                        self.read_sized_packet(self.read_size(remainder))
                        break

                    size = size_pack.unpack(remainder[:size_pack.size])[0]
                    remainder = remainder[size_pack.size:]
                    if len(remainder) <= size:
                        self.read_sized_packet(size, remainder)
                        break

                    self._packet(remainder[:size])
                    remainder = remainder[size:]
            else:
                self.read_sized_packet(self.read_size(tag))

            while True:
                self.read_sized_packet(self.read_size())
        except Disconnect:
            self.on_timeout()
        except zlib.error:
            self.on_invalid()
        except socket.timeout:
            return
        except BaseException:
            logger.exception('Error in base packet handling')
            raise
        finally:
            self.on_disconnect()

    def send(self, data):
        compressed = zlib.compress(data.encode('utf-8'))
        self.request.sendall(size_pack.pack(len(compressed)) + compressed)