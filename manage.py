#!/usr/bin/env python
import os
import sys

try:
    import MySQLdb  # noqa: F401, imported for side effect
except ImportError:
    import pymysql
    pymysql.install_as_MySQLdb()

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dmoj.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
