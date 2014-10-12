def ranker(iterable):
    rank = 0
    delta = 1
    last = -1
    for item in iterable:
        if item.points != last:
            rank += delta
            delta = 0
        delta += 1
        yield rank, item
        last = round(item.points, 1)
