from django.core.urlresolvers import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext as _

from judge.models import Submission
from judge.views.submission import ProblemSubmissions, ForceContestMixin
from judge.utils.problems import get_result_table

__all__ = ['RankedSubmissions']


class RankedSubmissions(ProblemSubmissions):
    dynamic_update = False

    def get_queryset(self):
        if self.in_contest:
            contest_join = '''INNER JOIN judge_contestsubmission AS cs ON (sub.id = cs.submission_id)
                              INNER JOIN judge_contestparticipation AS cp ON (cs.participation_id = cp.id)'''
            points = 'cs.points'
            constraint = 'AND cp.contest_id = %s'
        else:
            contest_join = ''
            points = 'sub.points'
            constraint = ''
        return super(RankedSubmissions, self).get_queryset().order_by('-points', 'time').extra(where=['''
            judge_submission.id IN (
                SELECT sub.id
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
            )
        '''.format(points=points, contest_join=contest_join, constraint=constraint)],
            params=(self.problem.id, self.contest.id) * 3 if self.in_contest else (self.problem.id,) * 3)

    def get_title(self):
        return _('Best solutions for %s') % self.problem.name

    def get_content_title(self):
        return format_html(_(u'Best solutions for <a href="{1}">{0}</a>'), self.problem.name,
                           reverse('problem_detail', args=[self.problem.code]))

    def get_result_table(self):
        return get_result_table(super(RankedSubmissions, self).get_queryset().order_by())


class ContestRankedSubmission(ForceContestMixin, RankedSubmissions):
    def get_title(self):
        return _('Best solutions for %s in %s') % (self.problem.name, self.contest.name)

    def get_content_title(self):
        return format_html(_(u'Best solutions for <a href="{1}">{0}</a> in <a href="{3}">{2}</a>'),
                           self.problem.name, reverse('problem_detail', args=[self.problem.code]),
                           self.contest.name, reverse('contest_view', args=[self.contest.key]))

    def get_result_table(self):
        return get_result_table(Submission.objects.filter(
            problem_id=self.problem.id, contest__participation__contest_id=self.contest.id))
