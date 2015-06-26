from django.core.cache import cache


def finished_submission(sub):
    keys = ['user_complete:%d' % sub.user_id]
    if hasattr(sub, 'contest'):
        participation = sub.contest.participation
        keys += ['contest_complete:%d' % participation.id]
    cache.delete_many(keys)
