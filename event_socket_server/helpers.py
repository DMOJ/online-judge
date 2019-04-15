import struct
import zlib

from judge.utils.unicode import utf8text

from .handler import Handler

size_pack = struct.Struct('!I')


class SizedPacketHandler(Handler):
    def __init__(self, server, socket):
        super(SizedPacketHandler, self).__init__(server, socket)
        self._buffer = b''
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
        return zlib.compress(data.encode('utf-8'))

    def packet(self, data):
        raise NotImplementedError()

    def _packet(self, data):
        try:
            self.packet(zlib.decompress(data).decode('utf-8'))
        except zlib.error as e:
            self.malformed_packet(e)

    def malformed_packet(self, exception):
        self.close()


class ProxyProtocolMixin(object):
    __UNKNOWN_TYPE = 0
    __PROXY1 = 1
    __PROXY2 = 2
    __DATA = 3

    __HEADER2 = b'\x0D\x0A\x0D\x0A\x00\x0D\x0A\x51\x55\x49\x54\x0A'
    __HEADER2_LEN = len(__HEADER2)

    _REAL_IP_SET = None

    @classmethod
    def with_proxy_set(cls, ranges):
        from netaddr import IPSet, IPGlob
        from itertools import chain

        globs = []
        addrs = []
        for item in ranges:
            if '*' in item or '-' in item:
                globs.append(IPGlob(item))
            else:
                addrs.append(item)
        ipset = IPSet(chain(chain.from_iterable(globs), addrs))
        return type(cls.__name__, (cls,), {'_REAL_IP_SET': ipset})

    def __init__(self, server, socket):
        super(ProxyProtocolMixin, self).__init__(server, socket)
        self.__buffer = b''
        self.__type = (self.__UNKNOWN_TYPE if self._REAL_IP_SET and
                       self.client_address[0] in self._REAL_IP_SET else self.__DATA)

    def __parse_proxy1(self, data):
        self.__buffer += data
        index = self.__buffer.find(b'\r\n')
        if 0 <= index < 106:
            proxy = data[:index].split()
            if len(proxy) < 2:
                return self.close()
            if proxy[1] == b'TCP4':
                if len(proxy) != 6:
                    return self.close()
                self.client_address = (utf8text(proxy[2]), utf8text(proxy[4]))
                self.server_address = (utf8text(proxy[3]), utf8text(proxy[5]))
            elif proxy[1] == b'TCP6':
                self.client_address = (utf8text(proxy[2]), utf8text(proxy[4]), 0, 0)
                self.server_address = (utf8text(proxy[3]), utf8text(proxy[5]), 0, 0)
            elif proxy[1] != b'UNKNOWN':
                return self.close()

            self.__type = self.__DATA
            super(ProxyProtocolMixin, self)._recv_data(data[index+2:])
        elif len(self.__buffer) > 107 or index > 105:
            self.close()

    def _recv_data(self, data):
        if self.__type == self.__DATA:
            super(ProxyProtocolMixin, self)._recv_data(data)
        elif self.__type == self.__UNKNOWN_TYPE:
            if len(data) >= 16 and data[:self.__HEADER2_LEN] == self.__HEADER2:
                self.close()
            elif len(data) >= 8 and data[:5] == b'PROXY':
                self.__type = self.__PROXY1
                self.__parse_proxy1(data)
            else:
                self.__type = self.__DATA
                super(ProxyProtocolMixin, self)._recv_data(data)
        else:
            self.__parse_proxy1(data)
