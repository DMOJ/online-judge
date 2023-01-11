import os

import gevent.monkey  # noqa: I100, gevent must be imported here

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmoj.settings')
gevent.monkey.patch_all()

# noinspection PyUnresolvedReferences
import dmoj_install_pymysql  # noqa: E402, F401, I100, I202, imported for side effect

from django.core.wsgi import get_wsgi_application  # noqa: E402, I100, I202, django must be imported here
application = get_wsgi_application()
