from .helpers import ProxyProtocolMixin, ZlibPacketHandler
from .server import Server


class EchoPacketHandler(ProxyProtocolMixin, ZlibPacketHandler):
    def __init__(self, server, socket):
        super(EchoPacketHandler, self).__init__(server, socket)
        self._gotdata = False
        self.server.schedule(5, self._kill_if_no_data)

    def _kill_if_no_data(self):
        if not self._gotdata:
            print('Inactive client:', self._socket.getpeername())
            self.close()

    def packet(self, data):
        self._gotdata = True
        print('Data from %s: %r' % (self._socket.getpeername(), data[:30] if len(data) > 30 else data))
        self.send(data)

    def on_close(self):
        self._gotdata = True
        print('Closed client:', self._socket.getpeername())


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--host', action='append')
    parser.add_argument('-p', '--port', type=int, action='append')
    try:
        import netaddr
    except ImportError:
        netaddr = None
    else:
        parser.add_argument('-P', '--proxy', action='append')
    args = parser.parse_args()

    handler = EchoPacketHandler
    if netaddr is not None and args.proxy:
        handler = handler.with_proxy_set(args.proxy)
    server = Server(list(zip(args.host, args.port)), handler)
    server.serve_forever()


if __name__ == '__main__':
    main()
