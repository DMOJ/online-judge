try:
    import MySQLdb  # noqa: F401, imported for side effect
except ImportError:
    import dmoj_install_pymysql  # noqa: F401, imported for side effect

# noinspection PyUnresolvedReferences
from dmoj.celery import app  # noqa: F401, imported for side effect
