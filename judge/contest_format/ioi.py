from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import connection
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from judge.contest_format.default import DefaultContestFormat
from judge.contest_format.registry import register_contest_format
from judge.timezone import from_database_time
from judge.utils.timedelta import nice_repr


@register_contest_format('ioi')
class IOIContestFormat(DefaultContestFormat):
    name = gettext_lazy('IOI')
    config_defaults = {'cumtime': False}
    '''
        cumtime: Specify True if time penalties are to be computed. Defaults to False.
    '''

    @classmethod
    def validate(cls, config):
        if config is None:
            return

        if not isinstance(config, dict):
            raise ValidationError('IOI-styled contest expects no config or dict as config')

        for key, value in config.items():
            if key not in cls.config_defaults:
                raise ValidationError('unknown config key "%s"' % key)
            if not isinstance(value, type(cls.config_defaults[key])):
                raise ValidationError('invalid type for config key "%s"' % key)

    def __init__(self, contest, config):
        self.config = self.config_defaults.copy()
        self.config.update(config or {})
        self.contest = contest

    def update_participation(self, participation):
        cumtime = 0
        points = 0
        format_data = {}

        with connection.cursor() as cursor:
            cursor.execute('''
            SELECT MAX(cs.points) as `score`, (
                SELECT MIN(csub.date)
                    FROM judge_contestsubmission ccs LEFT OUTER JOIN
                         judge_submission csub ON (csub.id = ccs.submission_id)
                    WHERE ccs.problem_id = cp.id AND ccs.participation_id = %s AND ccs.points = MAX(cs.points)
            ) AS `time`, cp.id AS `prob`
            FROM judge_contestproblem cp INNER JOIN
                 judge_contestsubmission cs ON (cs.problem_id = cp.id AND cs.participation_id = %s) LEFT OUTER JOIN
                 judge_submission sub ON (sub.id = cs.submission_id)
            GROUP BY cp.id
            ''', (participation.id, participation.id))

            for score, time, prob in cursor.fetchall():
                if self.config['cumtime']:
                    dt = (from_database_time(time) - participation.start).total_seconds()
                    if score:
                        cumtime += dt
                else:
                    dt = 0

                format_data[str(prob)] = {'time': dt, 'points': score}
                points += score

        participation.cumtime = max(cumtime, 0)
        participation.score = points
        participation.format_data = format_data
        participation.save()

    def display_user_problem(self, participation, contest_problem):
        format_data = (participation.format_data or {}).get(str(contest_problem.id))
        if format_data:
            return format_html(
                '<td class="{state}"><a href="{url}">{points}<div class="solving-time">{time}</div></a></td>',
                state=(('pretest-' if self.contest.run_pretests_only and contest_problem.is_pretested else '') +
                       self.best_solution_state(format_data['points'], contest_problem.points)),
                url=reverse('contest_user_submissions',
                            args=[self.contest.key, participation.user.user.username, contest_problem.problem.code]),
                points=floatformat(format_data['points']),
                time=nice_repr(timedelta(seconds=format_data['time']), 'noday') if self.config['cumtime'] else '',
            )
        else:
            return mark_safe('<td></td>')

    def display_participation_result(self, participation):
        return format_html(
            '<td class="user-points">{points}<div class="solving-time">{cumtime}</div></td>',
            points=floatformat(participation.score),
            cumtime=nice_repr(timedelta(seconds=participation.cumtime), 'noday') if self.config['cumtime'] else '',
        )
