from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.html import format_html

from judge.models import Problem, Submission, Contest
from judge.views.submission import ProblemSubmissions, ForceContestMixin
from judge.utils.problems import user_completed_ids, get_result_table
from judge.utils.diggpaginator import DiggPaginator


__all__ = ['RankedSubmissions']


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


class RankedSubmissions(ProblemSubmissions):
    def get_queryset(self):
        if self.in_contest:
            count = Submission.objects.filter(problem_id=self.problem.id,
                                              contest__participation__contest_id=self.contest.id, points__gt=0)\
                .values('user').distinct().count()
            contest_join = '''INNER JOIN judge_contestsubmission AS cs ON (sub.id = cs.submission_id)
                              INNER JOIN judge_contestparticipation AS cp ON (cs.participation_id = cp.id)'''
            points = 'cs.points'
            constraint = 'AND cp.contest_id = %s'
        else:
            count = Submission.objects.filter(problem__id=self.problem.id) \
                .filter(Q(result='AC') | Q(problem__partial=True, points__gt=0)).values('user').distinct().count()
            contest_join = ''
            points = 'sub.points'
            constraint = ''
        ranking = FancyRawQuerySetWrapper(Submission, count, '''
            SELECT sub.id, sub.user_id, sub.problem_id, sub.date, sub.time,
                   sub.memory, sub.points, sub.language_id,
                   sub.status, sub.result, sub.case_points, sub.case_total
            FROM (
                SELECT sub.user_id AS uid, MAX(sub.points) AS points
                FROM judge_submission AS sub INNER JOIN
                     judge_problem AS prob ON (sub.problem_id = prob.id) {contest_join}
                WHERE sub.problem_id = %s AND {points} > 0 {constraint}
                GROUP BY sub.user_id
            ) AS highscore INNER JOIN (
                SELECT sub.user_id AS uid, sub.points, MIN(sub.time) as time
                FROM judge_submission AS sub INNER JOIN
                     judge_problem AS prob ON (sub.problem_id = prob.id) {contest_join}
                WHERE sub.problem_id = %s AND {points} > 0 {constraint}
                GROUP BY sub.user_id, {points}
            ) AS fastest ON (highscore.uid = fastest.uid AND highscore.points = fastest.points)
                INNER JOIN judge_submission AS sub
                    ON (sub.user_id = fastest.uid AND sub.time = fastest.time) {contest_join}
            WHERE sub.problem_id = %s AND {points} > 0 {constraint}
            GROUP BY fastest.uid
            ORDER BY {points} DESC, sub.time ASC
        '''.format(points=points, contest_join=contest_join, constraint=constraint),
                  (self.problem.id, self.contest.id) * 3 if self.in_contest else (self.problem.id,) * 3)
        return ranking

    def get_title(self):
        return 'Best solutions for %s' % self.problem.name

    def get_content_title(self):
        return format_html(u'Best solutions for <a href="{1}">{0}</a>', self.problem.name,
                           reverse('problem_detail', args=[self.problem.code]))

    def get_result_table(self):
        return get_result_table(super(RankedSubmissions, self).get_queryset())


class ContestRankedSubmission(ForceContestMixin, RankedSubmissions):
    def get_title(self):
        return 'Best solutions for %s in %s' % (self.problem.name, self.contest.name)

    def get_content_title(self):
        return format_html(u'Best solutions for <a href="{1}">{0}</a> in <a href="{3}">{2}</a>',
                           self.problem.name, reverse('problem_detail', args=[self.problem.code]),
                           self.contest.name, reverse('contest_view', args=[self.contest.key]))

    def get_result_table(self):
        return get_result_table(Submission.objects.filter(
            problem_id=self.problem.id, contest__participation__contest_id=self.contest_id))