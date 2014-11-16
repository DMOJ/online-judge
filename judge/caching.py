from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key


def update_submission(id):
    key = 'version:submission-%d' % id
    cache.add(key, 0, None)
    cache.incr(key)


def update_stats():
    cache.delete('sub_stats_table')
    cache.delete('sub_stats_data')


def point_update(profile):
    cache.delete(make_template_fragment_key('global_user'))


def finished_submission(sub):
    cache.delete('user_complete:%d' % sub.user_id)
    cache.delete('user_probs:%d' % sub.user_id)
    cache.delete('problem_rank:%d' % sub.problem_id)
    if hasattr(sub, 'contest'):
        participation = sub.contest.participation
        cache.delete('contest_complete:%d' % participation.id)
        cache.delete('contest_problem_rank:%d:%d' % (participation.contest_id, sub.problem_id))
        cache.delete(make_template_fragment_key('conrank_user_prob',
                                                (participation.profile.user_id,
                                                 participation.contest_id)))