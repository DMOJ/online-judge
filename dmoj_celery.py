import os

try:
    import MySQLdb  # noqa: F401, imported for side effect
except ImportError:
    import dmoj_install_pymysql  # noqa: F401, imported for side effect

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmoj.settings')

# noinspection PyUnresolvedReferences
import django_2_2_pymysql_patch  # noqa: I100, F401, I202, imported for side effect

# noinspection PyUnresolvedReferences
from dmoj.celery import app  # noqa: F401, imported for side effect
