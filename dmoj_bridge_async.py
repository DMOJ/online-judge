import os

import gevent.monkey  # noqa: I100, gevent must be imported here

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmoj.settings')
gevent.monkey.patch_all()

# noinspection PyUnresolvedReferences
import dmoj_install_pymysql  # noqa: E402, F401, I100, I202, imported for side effect

import django  # noqa: E402, F401, I100, I202, django must be imported here
django.setup()

from judge.bridge.daemon import judge_daemon  # noqa: E402, I100, I202, django code must be imported here

if __name__ == '__main__':
    judge_daemon()
