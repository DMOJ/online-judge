from operator import attrgetter


def ranker(iterable, key=attrgetter('points'), rank=0):
    delta = 1
    last = None
    for item in iterable:
        new = key(item)
        if new != last:
            rank += delta
            delta = 0
        delta += 1
        yield rank, item
        last = key(item)
