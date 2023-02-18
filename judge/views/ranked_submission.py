from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from judge.models import Language, Submission
from judge.utils.problems import get_result_data
from judge.utils.raw_sql import join_sql_subquery
from judge.views.submission import ForceContestMixin, ProblemSubmissions

__all__ = ['RankedSubmissions', 'ContestRankedSubmission']


class RankedSubmissions(ProblemSubmissions):
    tab = 'best_submissions_list'
    dynamic_update = False

    def get_queryset(self):
        params = [self.problem.id]
        if self.in_contest:
            contest_join = 'INNER JOIN judge_contestsubmission AS cs ON (sub.id = cs.submission_id)'
            points = 'cs.points'
            constraint = ' AND sub.contest_object_id = %s'
            params.append(self.contest.id)
        else:
            contest_join = ''
            points = 'sub.points'
            constraint = ''

        if self.selected_languages:
            lang_ids = Language.objects.filter(key__in=self.selected_languages).values_list('id', flat=True)
            if lang_ids:
                constraint += f' AND sub.language_id IN ({", ".join(["%s"] * len(lang_ids))})'
                params.extend(lang_ids)
            self.selected_languages = set()

        queryset = super(RankedSubmissions, self).get_queryset().filter(user__is_unlisted=False)
        join_sql_subquery(
            queryset,
            subquery="""
                SELECT sub.id AS id
                FROM (
                    SELECT sub.user_id AS uid, MAX(sub.points) AS points
                    FROM judge_submission AS sub {contest_join}
                    WHERE sub.problem_id = %s AND {points} > 0 {constraint}
                    GROUP BY sub.user_id
                ) AS highscore STRAIGHT_JOIN (
                    SELECT sub.user_id AS uid, sub.points, MIN(sub.time) as time
                    FROM judge_submission AS sub {contest_join}
                    WHERE sub.problem_id = %s AND {points} > 0 {constraint}
                    GROUP BY sub.user_id, {points}
                ) AS fastest ON (highscore.uid = fastest.uid AND highscore.points = fastest.points)
                    STRAIGHT_JOIN judge_submission AS sub
                        ON (sub.user_id = fastest.uid AND sub.time = fastest.time)
                WHERE sub.problem_id = %s {constraint}
                GROUP BY sub.user_id
            """.format(points=points, contest_join=contest_join, constraint=constraint),
            params=params * 3, alias='best_subs', join_fields=[('id', 'id')], related_model=Submission,
        )

        if self.in_contest:
            return queryset.order_by('-contest__points', 'time')
        else:
            return queryset.order_by('-points', 'time')

    def get_title(self):
        return _('Best solutions for %s') % self.problem_name

    def get_content_title(self):
        return mark_safe(escape(_('Best solutions for %s')) % (
            format_html('<a href="{1}">{0}</a>', self.problem_name,
                        reverse('problem_detail', args=[self.problem.code])),
        ))

    def _get_result_data(self, queryset=None):
        if queryset is None:
            queryset = super(RankedSubmissions, self).get_queryset()
        return get_result_data(queryset.order_by())


class ContestRankedSubmission(ForceContestMixin, RankedSubmissions):
    def get_title(self):
        if self.problem.is_accessible_by(self.request.user):
            return _('Best solutions for %(problem)s in %(contest)s') % {
                'problem': self.problem_name, 'contest': self.contest.name,
            }
        return _('Best solutions for problem %(number)s in %(contest)s') % {
            'number': self.get_problem_number(self.problem), 'contest': self.contest.name,
        }

    def get_content_title(self):
        if self.problem.is_accessible_by(self.request.user):
            return mark_safe(escape(_('Best solutions for %(problem)s in %(contest)s')) % {
                'problem': format_html('<a href="{1}">{0}</a>', self.problem_name,
                                       reverse('problem_detail', args=[self.problem.code])),
                'contest': format_html('<a href="{1}">{0}</a>', self.contest.name,
                                       reverse('contest_view', args=[self.contest.key])),
            })
        return mark_safe(escape(_('Best solutions for problem %(number)s in %(contest)s')) % {
            'number': self.get_problem_number(self.problem),
            'contest': format_html('<a href="{1}">{0}</a>', self.contest.name,
                                   reverse('contest_view', args=[self.contest.key])),
        })

    def _get_queryset(self):
        return super()._get_queryset().filter(contest_object=self.contest)
