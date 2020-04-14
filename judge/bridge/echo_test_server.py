from judge.bridge.base_handler import ZlibPacketHandler


class EchoPacketHandler(ZlibPacketHandler):
    def on_connect(self):
        print('New client:', self.client_address)
        self.timeout = 5

    def on_timeout(self):
        print('Inactive client:', self.client_address)

    def on_packet(self, data):
        self.timeout = None
        print('Data from %s: %r' % (self.client_address, data[:30] if len(data) > 30 else data))
        self.send(data)

    def on_disconnect(self):
        print('Closed client:', self.client_address)


def main():
    import argparse
    from judge.bridge.server import Server

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--host', action='append')
    parser.add_argument('-p', '--port', type=int, action='append')
    parser.add_argument('-P', '--proxy', action='append')
    args = parser.parse_args()

    class Handler(EchoPacketHandler):
        proxies = args.proxy or []

    server = Server(list(zip(args.host, args.port)), Handler)
    server.serve_forever()


if __name__ == '__main__':
    main()
