from django.utils.functional import lazy


class LazyMemoizedCallable:
    sentinel = object()

    def __init__(self, func):
        self.value = self.sentinel
        self.func = func

    def __call__(self):
        if self.value is self.sentinel:
            self.value = self.func()
        return self.value


def memo_lazy(func, result_type):
    return lazy(LazyMemoizedCallable(func), result_type)()
