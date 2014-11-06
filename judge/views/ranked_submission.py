from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.models import Problem, Submission
from judge.utils.diggpaginator import DiggPaginator
from judge.views import get_result_table, user_completed_ids


__all__ = ['ranked_submissions']


class FancyRawQuerySetWrapper(object):
    def __init__(self, type, count, query, args):
        self._count = count
        self._type = type
        self._query = query
        self._args = args

    def count(self):
        return self._count

    def __getitem__(self, item):
        if isinstance(item, slice):
            offset = item.start
            limit = item.stop - item.start
        else:
            offset = item
            limit = 1
        return list(Submission.objects.raw(self._query + 'LIMIT %s OFFSET %s', self._args + (limit, offset)))


def ranked_submissions(request, code, page=1):
    try:
        problem = Problem.objects.get(code=code)
    except ObjectDoesNotExist:
        raise Http404()
    results = FancyRawQuerySetWrapper(Submission,
                                      Submission.objects.filter(problem__id=problem.id).filter(
                                          Q(result='AC') | Q(problem__partial=True, points__gt=0)
                                      ).values('user').distinct().count(), '''
        SELECT subs.id, subs.user_id, subs.problem_id, subs.date, subs.time,
               subs.memory, subs.points, subs.language_id, subs.source,
               subs.status, subs.result
        FROM (
            SELECT sub.user_id AS uid, MAX(sub.points) AS points
            FROM judge_submission AS sub INNER JOIN
                 judge_problem AS prob ON (sub.problem_id = prob.id)
            WHERE sub.problem_id = %s AND
                 (sub.result = 'AC' OR (prob.partial AND sub.points > 0))
            GROUP BY sub.user_id
        ) AS highscore INNER JOIN (
            SELECT sub.user_id AS uid, sub.points, MIN(sub.time) as time
            FROM judge_submission AS sub INNER JOIN
                 judge_problem AS prob ON (sub.problem_id = prob.id)
            WHERE sub.problem_id = %s AND
                 (sub.result = 'AC' OR (prob.partial AND sub.points > 0))
            GROUP BY sub.user_id, sub.points
        ) AS fastest
                ON (highscore.uid = fastest.uid AND highscore.points = fastest.points)
            INNER JOIN (SELECT * FROM judge_submission WHERE problem_id = %s) as subs
                ON (subs.user_id = fastest.uid AND subs.time = fastest.time)
        GROUP BY fastest.uid
        ORDER BY subs.points DESC, subs.time ASC
    ''', (problem.id,) * 3)

    paginator = DiggPaginator(results, 50, body=6, padding=2)
    try:
        submissions = paginator.page(page)
    except PageNotAnInteger:
        submissions = paginator.page(1)
    except EmptyPage:
        submissions = paginator.page(paginator.num_pages)
    return render_to_response('submissions.jade',
                              {'submissions': submissions,
                               'results': get_result_table(problem__code=code),
                               'completed_problem_ids': user_completed_ids(request.user.profile)
                                    if request.user.is_authenticated() else [],
                               'dynamic_update': False,
                               'title': "Best solutions for %s" % problem.name,
                               'show_problem': False},
                              context_instance=RequestContext(request))