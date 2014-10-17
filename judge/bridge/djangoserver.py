from event_socket_server import get_preferred_engine


class DjangoServer(get_preferred_engine()):
    def __init__(self, judges, *args, **kwargs):
        super(DjangoServer, self).__init__(*args, **kwargs)
        self.judges = judges
