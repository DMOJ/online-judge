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


@register_contest_format('ecoo')
class ECOOContestFormat(DefaultContestFormat):
    name = gettext_lazy('ECOO')
    config_defaults = {'cumtime': False, 'first_ac_bonus': 10, 'time_bonus': 5}
    config_validators = {'cumtime': lambda x: True, 'first_ac_bonus': lambda x: x >= 0, 'time_bonus': lambda x: x >= 0}
    '''
        cumtime: Specify True if cumulative time is to be used in breaking ties. Defaults to False.
        first_ac_bonus: The number of points to award if a solution gets AC on its first non-IE/CE run. Defaults to 10.
        time_bonus: Number of minutes to award an extra point for submitting before the contest end.
                    Specify 0 to disable. Defaults to 5.
    '''

    @classmethod
    def validate(cls, config):
        if config is None:
            return

        if not isinstance(config, dict):
            raise ValidationError('ECOO-styled contest expects no config or dict as config')

        for key, value in config.items():
            if key not in cls.config_defaults:
                raise ValidationError('unknown config key "%s"' % key)
            if not isinstance(value, type(cls.config_defaults[key])):
                raise ValidationError('invalid type for config key "%s"' % key)
            if not cls.config_validators[key](value):
                raise ValidationError('invalid value "%s" for config key "%s"' % (value, key))

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
            SELECT (
                SELECT MAX(ccs.points)
                    FROM judge_contestsubmission ccs LEFT OUTER JOIN
                         judge_submission csub ON (csub.id = ccs.submission_id)
                    WHERE ccs.problem_id = cp.id AND ccs.participation_id = %s AND csub.date = MAX(sub.date)
            ) AS `score`, MAX(sub.date) AS `time`, cp.id AS `prob`, (
                SELECT COUNT(ccs.id)
                    FROM judge_contestsubmission ccs LEFT OUTER JOIN
                         judge_submission csub ON (csub.id = ccs.submission_id)
                    WHERE ccs.problem_id = cp.id AND ccs.participation_id = %s AND csub.result NOT IN ('IE', 'CE')
            ) AS `subs`, cp.points AS `max_score`
                FROM judge_contestproblem cp INNER JOIN
                     judge_contestsubmission cs ON (cs.problem_id = cp.id AND cs.participation_id = %s) LEFT OUTER JOIN
                     judge_submission sub ON (sub.id = cs.submission_id)
                GROUP BY cp.id
            ''', (participation.id, participation.id, participation.id))

            for score, time, prob, subs, max_score in cursor.fetchall():
                time = from_database_time(time)
                dt = (time - participation.start).total_seconds()
                if self.config['cumtime']:
                    cumtime += dt

                bonus = 0
                if score > 0:
                    # First AC bonus
                    if subs == 1 and score == max_score:
                        bonus += self.config['first_ac_bonus']
                    # Time bonus
                    if self.config['time_bonus']:
                        bonus += (participation.end_time - time).total_seconds() // 60 // self.config['time_bonus']
                    points += bonus

                format_data[str(prob)] = {'time': dt, 'points': score, 'bonus': bonus}
                points += score

        participation.cumtime = cumtime
        participation.score = points
        participation.format_data = format_data
        participation.save()

    def display_user_problem(self, participation, contest_problem):
        format_data = (participation.format_data or {}).get(str(contest_problem.id))
        if format_data:
            bonus = format_html('<small> +{bonus}</small>',
                                bonus=floatformat(format_data['bonus'])) if format_data['bonus'] else ''

            return format_html(
                '<td class="{state}"><a href="{url}">{points}{bonus}<div class="solving-time">{time}</div></a></td>',
                state=('pretest-' if self.contest.run_pretests_only and contest_problem.is_pretested else '') +
                       self.best_solution_state(format_data['points'], contest_problem.points),
                url=reverse('contest_user_submissions',
                            args=[self.contest.key, participation.user.user.username, contest_problem.problem.code]),
                points=floatformat(format_data['points']),
                bonus=bonus,
                time=nice_repr(timedelta(seconds=format_data['time']), 'noday'),
            )
        else:
            return mark_safe('<td></td>')

    def display_participation_result(self, participation):
        return format_html(
            '<td class="user-points">{points}<div class="solving-time">{cumtime}</div></td>',
            points=floatformat(participation.score),
            cumtime=nice_repr(timedelta(seconds=participation.cumtime), 'noday') if self.config['cumtime'] else '',
        )
