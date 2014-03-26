import threading
import time
import SocketServer


class DjangoServer(SocketServer.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, judges, *args, **kwargs):
        SocketServer.ThreadingTCPServer.__init__(self, *args, **kwargs)
        self.judges = judges
        self.ping_thread = threading.Thread(target=self.ping, args=())
        self.ping_thread.start()

    def ping(self):
        while True:
            for judge in self.judges:
                judge._send({'name': 'ping',
                             'when': time.time()})
            time.sleep(0.2)
