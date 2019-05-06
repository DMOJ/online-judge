try:
    import MySQLdb
except ImportError:
    import pymysql
    pymysql.install_as_MySQLdb()

# noinspection PyUnresolvedReferences
from dmoj.celery import app
