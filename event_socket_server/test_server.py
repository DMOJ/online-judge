from .helpers import ZlibPacketHandler
from .engines import engines

__author__ = 'Quantum'


class EchoPacketHandler(ZlibPacketHandler):
    def __init__(self, server, socket):
        super(EchoPacketHandler, self).__init__(server, socket)
        self._gotdata = False
        self.server.schedule(5, self._kill_if_no_data)

    def _kill_if_no_data(self):
        if not self._gotdata:
            print 'Inactive client:', self._socket.getpeername()
            self.close()

    def packet(self, data):
        self._gotdata = True
        print 'Data from %s: %r' % (self._socket.getpeername(), data[:30] if len(data) > 30 else data)
        self.send(data)

    def on_close(self):
        self._gotdata = True
        print 'Closed client:', self._socket.getpeername()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--host', default='localhost')
    parser.add_argument('-p', '--port', default=9999, type=int)
    parser.add_argument('-e', '--engine', default='select', choices=sorted(engines.keys()))
    args = parser.parse_args()

    class TestServer(engines[args.engine]):
        def _accept(self):
            client = super(TestServer, self)._accept()
            print 'New connection:', client.socket.getpeername()
            return client

    server = TestServer(args.host, args.port, EchoPacketHandler)
    server.serve_forever()

if __name__ == '__main__':
    main()