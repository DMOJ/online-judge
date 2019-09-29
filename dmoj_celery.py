try:
    import MySQLdb  # noqa: F401, imported for side effect
except ImportError:
    import pymysql
    pymysql.install_as_MySQLdb()

# noinspection PyUnresolvedReferences
from dmoj.celery import app  # noqa: F401, imported for side effect
