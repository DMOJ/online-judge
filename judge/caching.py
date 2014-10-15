from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.utils.cache import get_cache_key


def update_submission(id):
    key = 'version:submission-%d' % id
    cache.add(key, 0, None)
    cache.incr(key)


def update_stats():
    request = HttpRequest()
    request.path = reverse('judge.views.statistics_table_query')
    cache.delete(get_cache_key(request))
