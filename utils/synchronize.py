from functools import wraps
from threading import RLock


def synchronized(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        with self.__lock__:
            return func(self, *args, **kwargs)


def synchronize_class(cls):
    old_new = cls.__new__

    @wraps(old_new)
    def new(cls, *args, **kwargs):
        obj = old_new(cls, *args, **kwargs)
        obj.__lock__ = RLock()
        return obj
    cls.__new__ = new
    return cls