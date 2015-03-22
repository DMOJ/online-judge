from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key


def finished_submission(sub):
    keys = ['user_complete:%d' % sub.user_id]
    if hasattr(sub, 'contest'):
        participation = sub.contest.participation
        keys += ['contest_complete:%d' % participation.id]
    cache.delete_many(keys)
