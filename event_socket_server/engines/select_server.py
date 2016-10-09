import select

from ..base_server import BaseServer


class SelectServer(BaseServer):
    def __init__(self, *args, **kwargs):
        super(SelectServer, self).__init__(*args, **kwargs)
        self._reads = set(self._servers)
        self._writes = set()

    def _register_write(self, client):
        self._writes.add(client)

    def _register_read(self, client):
        self._writes.remove(client)

    def _clean_up_client(self, client, finalize=False):
        self._writes.discard(client)
        self._reads.remove(client)
        super(SelectServer, self)._clean_up_client(client, finalize)

    def _serve(self, select=select.select):
        for server in self._servers:
            server.listen(16)
        try:
            while not self._stop.is_set():
                r, w, x = select(self._reads, self._writes, self._reads, self._dispatch_event())
                for s in r:
                    if s in self._servers:
                        self._reads.add(self._accept(s))
                    else:
                        self._nonblock_read(s)

                for client in w:
                    self._nonblock_write(client)

                for s in x:
                    s.close()
                    if s in self._servers:
                        raise RuntimeError('Server is in exceptional condition')
                    else:
                        self._clean_up_client(s)
        finally:
            self.on_shutdown()
            for client in self._clients:
                self._clean_up_client(client, True)
            for server in self._servers:
                server.close()
