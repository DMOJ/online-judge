from django.core.cache import cache


def update_submission(id):
    key = 'version:submission-%d' % id
    cache.add(key, 0, None)
    cache.incr(key)


def update_stats():
    cache.delete('sub_stats_table')
    cache.delete('sub_stats_data')


def finished_submission(sub):
    cache.delete('prob_users:%d' % sub.problem_id)