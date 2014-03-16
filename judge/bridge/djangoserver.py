import SocketServer


class DjangoServer(SocketServer.ThreadingTCPServer):
    def __init__(self, judges, *args, **kwargs):
        SocketServer.ThreadingTCPServer.__init__(self, *args, **kwargs)
        self.judges = judges
