from operator import attrgetter


def ranker(iterable, key=attrgetter('points')):
    rank = 0
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


def tie_ranker(iterable, key=attrgetter('points')):
    rank = 0
    delta = 1
    last = None
    buf = []
    for item in iterable:
        new = key(item)
        if new != last:
            for i in buf:
                yield rank + delta / 2.0, i
            rank += delta
            delta = 0
            buf = []
        delta += 1
        buf.append(item)
        last = key(item)
    for i in buf:
        yield rank + delta / 2.0, i
