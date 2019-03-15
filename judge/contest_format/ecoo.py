from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import connection
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from judge.contest_format.base import BaseContestFormat
from judge.contest_format.registry import register_contest_format
from judge.timezone import from_database_time
from judge.utils.timedelta import nice_repr

@register_contest_format('ecoo')
class ECOOContestFormat(BaseContestFormat):
    name = gettext_lazy('ECOO')

    @classmethod
    def validate(cls, config):
        if config is not None and (not isinstance(config, dict) or config):
            raise ValidationError('ECOO contest expects no config or empty dict as config')


    def __init__(self, contest, config):
        super(ECOOContestFormat, self).__init__(contest, config)


    def update_participation(self, participation):
        points = 0
        format_data = {}

        with connection.cursor() as cursor:
            cursor.execute('''
            SELECT (
                SELECT MAX(ccs.points)
                    FROM judge_contestsubmission ccs LEFT OUTER JOIN
                         judge_submission csub ON (csub.id = ccs.submission_id)
                    WHERE ccs.problem_id = cp.id AND ccs.participation_id = %s AND csub.date = MAX(sub.date)
                ) AS `score`, MAX(sub.date) AS `time`, cp.id AS `prob`, COUNT(sub.id) AS `subs`, cp.points AS `max_score`
                FROM judge_contestproblem cp INNER JOIN
                     judge_contestsubmission cs ON (cs.problem_id = cp.id AND cs.participation_id = %s) LEFT OUTER JOIN
                     judge_submission sub ON (sub.id = cs.submission_id)
                GROUP BY cp.id
            ''', (participation.id, participation.id))
            for score, time, prob, subs, max_score in cursor.fetchall():
                time = from_database_time(time)
                dt = (time - participation.start).total_seconds()
                # First AC bonus
                bonus = 0
                if subs == 1 and score == max_score:
                    bonus = 10
                # Cast to int is needed because cursor returns a long
                format_data[str(int(prob))] = {'time': dt, 'points': score, 'bonus': bonus}
                points += score
                # Compute time bonus
                bonus += (participation.end_time - time).total_seconds() // 60 // 5
                if score > 0:
                    points += bonus

        participation.cumtime = 0
        participation.score = points
        participation.format_data = format_data
        participation.save()

    def display_user_problem(self, participation, contest_problem):
        format_data = (participation.format_data or {}).get(str(contest_problem.id))
        if format_data:
            return format_html(
                u'<td class="{state}"><a href="{url}">{points}<div class="solving-time">{time}</div></a></td>',
                state=('pretest-' if contest_problem.is_pretested else '') +
                      self.best_solution_state(format_data['points'], contest_problem.points),
                url=reverse('contest_user_submissions',
                            args=[self.contest.key, participation.user.user.username, contest_problem.problem.code]),
                points=floatformat(format_data['points']+format_data['bonus']),
                time=nice_repr(timedelta(seconds=format_data['time']), 'noday'),
            )
        else:
            return mark_safe('<td></td>')


    def display_participation_result(self, participation):
        return format_html(
            u'<td class="user-points">{points}</td>',
            points=floatformat(participation.score),
        )

    def get_problem_breakdown(self, participation, contest_problems):
        return [(participation.format_data or {}).get(str(contest_problem.id)) for contest_problem in contest_problems]
