import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmoj.settings')

import pymysql
pymysql.install_as_MySQLdb()

import gevent.monkey
gevent.monkey.patch_all()

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
