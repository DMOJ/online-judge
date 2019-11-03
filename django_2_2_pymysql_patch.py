import django
from django.utils.encoding import force_text

if (2, 2) <= django.VERSION < (3,):
    # Django 2.2.x is incompatible with PyMySQL.
    # This monkey patch backports the Django 3.0+ code.

    from django.db.backends.mysql.operations import DatabaseOperations

    def last_executed_query(self, cursor, sql, params):
        # With MySQLdb, cursor objects have an (undocumented) "_executed"
        # attribute where the exact query sent to the database is saved.
        # See MySQLdb/cursors.py in the source distribution.
        # MySQLdb returns string, PyMySQL bytes.
        return force_text(getattr(cursor, '_executed', None), errors='replace')

    DatabaseOperations.last_executed_query = last_executed_query
