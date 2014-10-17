import select
from ..base_server import BaseServer
__author__ = 'Quantum'


class SelectServer(BaseServer):
    def __init__(self, *args, **kwargs):
        super(SelectServer, self).__init__(*args, **kwargs)
        self._reads = set([self._server])
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
        self._server.listen(16)
        try:
            while not self._stop.is_set():
                r, w, x = select(self._reads, self._writes, self._reads, self._dispatch_event())
                for s in r:
                    if s is self._server:
                        self._reads.add(self._accept())
                    else:
                        self._nonblock_read(s)

                for client in w:
                    self._nonblock_write(client)

                for s in x:
                    s.close()
                    if s is self._server:
                        raise RuntimeError('Server is in exceptional condition')
                    else:
                        self._clean_up_client(s)
        finally:
            for client in self._clients:
                self._clean_up_client(client, True)
            self._server.close()