from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.utils.cache import get_cache_key


def update_submission(id):
    key = 'version:submission-%d' % id
    cache.add(key, 0, None)
    cache.incr(key)


def update_stats():
    cache.delete('sub_stats_table')
