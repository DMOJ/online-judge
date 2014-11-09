from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from judge.models import Submission


def update_submission(id):
    key = 'version:submission-%d' % id
    cache.add(key, 0, None)
    cache.incr(key)


def update_stats():
    cache.delete('sub_stats_table')
    cache.delete('sub_stats_data')


def finished_submission(sub):
    assert isinstance(sub, Submission)
    cache.delete('prob_users:%d' % sub.problem_id)
    cache.delete('user_complete:%d' % sub.user_id)
    if hasattr(sub, 'contest'):
        participation = sub.contest.participation
        cache.delete('contest_complete:%d' % participation.id)
        cache.delete(make_template_fragment_key('conrank_user_prob',
                                                (participation.profile.user_id,
                                                 participation.contest_id)))