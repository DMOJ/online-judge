from django.conf import settings
from django.db.models import Max

from judge.models import Problem

from collections import namedtuple

PP_STEP = getattr(settings, 'PP_STEP', 0.95)
PP_ENTRIES = getattr(settings, 'PP_ENTRIES', 100)
PP_WEIGHT_TABLE = [pow(PP_STEP, i) for i in xrange(PP_ENTRIES)]

PPBreakdown = namedtuple('PPBreakdown', 'points weight scaled_points problem_name problem_code date')


def get_pp_breakdown(user):
    data = (Problem.objects.filter(submission__user=user, submission__points__isnull=False, is_public=True)
            .annotate(max_points=Max('submission__points')).order_by('-max_points')
            .values('max_points', 'name', 'code', 'submission__date').filter(max_points__gt=0))

    breakdown = []
    for weight, contrib in zip(PP_WEIGHT_TABLE, data):
        points = contrib['max_points']
        breakdown.append(PPBreakdown(points=points,
                                     weight=weight,
                                     scaled_points=points * weight,
                                     problem_name=contrib['name'],
                                     problem_code=contrib['code'],
                                     date=contrib['submission__date']))

    return pp
