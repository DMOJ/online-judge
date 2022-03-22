from itertools import zip_longest


def chunk(iterable, size):
    fill = object()
    for group in zip_longest(*[iter(iterable)] * size, fillvalue=fill):
        yield [item for item in group if item is not fill]
