from itertools import chain

from django.db import connection, transaction


class LockModel(object):
    def __init__(self, write, read=()):
        self.tables = ', '.join(chain(
            ('`%s` WRITE' % model._meta.db_table for model in write),
            ('`%s` READ' % model._meta.db_table for model in read),
        ))
        self.cursor = connection.cursor()

    def __enter__(self):
        self.cursor.execute('LOCK TABLES ' + self.tables)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            transaction.commit()
        else:
            transaction.rollback()
        self.cursor.execute('UNLOCK TABLES')
        self.cursor.close()
