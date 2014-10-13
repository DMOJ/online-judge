from django.core.cache import cache


def update_submission(id):
    key = 'version:submission-%d' % id
    cache.add(key, 0)
    cache.incr(key)