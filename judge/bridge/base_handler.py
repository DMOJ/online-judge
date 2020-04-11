import logging
import socket
import struct
import zlib
from itertools import chain

from netaddr import IPGlob, IPSet

from judge.utils.unicode import utf8text

logger = logging.getLogger('judge.bridge')

size_pack = struct.Struct('!I')
assert size_pack.size == 4
PROXY_MAGIC = size_pack.unpack(b'PROX')[0]


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


# socketserver.BaseRequestHandler does all the handling in __init__,
# making it impossible to inherit __init__ sanely. While it lets you
# use setup(), most tools will complain about uninitialized variables.
# This metaclass will allow sane __init__ behaviour while also magically
# calling the methods that handles the request.
class RequestHandlerMeta(type):
    def __call__(cls, *args, **kwargs):
        handler = super().__call__(*args, **kwargs)
        handler.on_connect()
        try:
            handler.handle()
        finally:
            handler.on_disconnect()


class ZlibPacketHandler(metaclass=RequestHandlerMeta):
    proxies = []

    def __init__(self, request, client_address, server):
        self.request = request
        self.server = server
        self.client_address = client_address
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
            assert remainder >= 0

        while remainder:
            data = self.request.recv(remainder)
            remainder -= len(data)
            buffer.append(data)
        self._on_packet(b''.join(buffer))

    def parse_proxy_protocol(self, line):
        words = line.split()

        if len(words) < 2:
            raise Disconnect()

        if words[1] == b'TCP4':
            if len(words) != 6:
                raise Disconnect()
            self.client_address = (utf8text(words[2]), utf8text(words[4]))
            self.server_address = (utf8text(words[3]), utf8text(words[5]))
        elif words[1] == b'TCP6':
            self.client_address = (utf8text(words[2]), utf8text(words[4]), 0, 0)
            self.server_address = (utf8text(words[3]), utf8text(words[5]), 0, 0)
        elif words[1] != b'UNKNOWN':
            raise Disconnect()

    def read_size(self, buffer=b''):
        while len(buffer) < size_pack.size:
            recv = self.request.recv(size_pack.size - len(buffer))
            if not recv:
                raise Disconnect()
            buffer += recv
        return size_pack.unpack(buffer)[0]

    def read_proxy_header(self, buffer=b''):
        # Max line length for PROXY protocol is 107, and we received 4 already.
        while b'\r\n' not in buffer:
            if len(buffer) > 107:
                raise Disconnect()
            data = self.request.recv(107)
            if not data:
                raise Disconnect()
            buffer += data
        return buffer

    def _on_packet(self, data):
        self.on_packet(zlib.decompress(data).decode('utf-8'))

    def on_packet(self, data):
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
        try:
            tag = self.read_size()
            if self.client_address[0] in self.proxies and tag == PROXY_MAGIC:
                proxy, _, remainder = self.read_proxy_header(b'PROX').partition(b'\r\n')
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

                    self._on_packet(remainder[:size])
                    remainder = remainder[size:]
            else:
                self.read_sized_packet(tag)

            while True:
                self.read_sized_packet(self.read_size())
        except Disconnect:
            return
        except zlib.error:
            self.on_invalid()
        except socket.timeout:
            logger.warning('Socket timed out: %s', self.client_address)
        except BaseException:
            logger.exception('Error in base packet handling')
            raise

    def send(self, data):
        compressed = zlib.compress(data.encode('utf-8'))
        self.request.sendall(size_pack.pack(len(compressed)) + compressed)

    def close(self):
        self.request.shutdown(socket.SHUT_RDWR)
