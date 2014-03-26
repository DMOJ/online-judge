import SocketServer


class DjangoServer(SocketServer.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, judges, *args, **kwargs):
        SocketServer.ThreadingTCPServer.__init__(self, *args, **kwargs)
        self.judges = judges


    def ping(self):
        while True:
            for judge in self.judges:
                judge._send({'name': 'ping'})
            import time
            time.sleep(0.2)
