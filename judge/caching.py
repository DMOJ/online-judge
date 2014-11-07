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
    cache.delete('prob_users:%d' % sub.problem_id)
    assert isinstance(sub, Submission)
    if hasattr(sub, 'contest'):
        participation = sub.contest.participation
        cache.delete(make_template_fragment_key('conrank_user_prob',
                                                (participation.profile.user_id,
                                                 participation.contest_id)))