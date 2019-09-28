import os

import gevent.monkey

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmoj.settings')
gevent.monkey.patch_all()

try:
    import MySQLdb  # noqa: F401, imported for side effect
except ImportError:
    import pymysql
    pymysql.install_as_MySQLdb()
else:
    from functools import wraps, partial
    import gevent.hub

    def gevent_waiter(fd, hub=gevent.hub.get_hub()):
        hub.wait(hub.loop.io(fd, 1))

    MySQLdb.connect = MySQLdb.Connection = MySQLdb.Connect = wraps(MySQLdb.connect)(
        partial(MySQLdb.connect, waiter=gevent_waiter)
    )

from django.core.wsgi import get_wsgi_application  # noqa: E402, I202, django must be imported here
application = get_wsgi_application()
