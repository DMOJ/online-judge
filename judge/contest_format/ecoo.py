from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Count, Max, OuterRef, Subquery
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _, gettext_lazy, ngettext

from judge.contest_format.default import DefaultContestFormat
from judge.contest_format.registry import register_contest_format
from judge.utils.timedelta import nice_repr


@register_contest_format('ecoo')
class ECOOContestFormat(DefaultContestFormat):
    name = gettext_lazy('ECOO')
    config_defaults = {'cumtime': False, 'first_ac_bonus': 10, 'time_bonus': 5}
    config_validators = {'cumtime': lambda x: True, 'first_ac_bonus': lambda x: x >= 0, 'time_bonus': lambda x: x >= 0}
    """
        cumtime: Specify True if cumulative time is to be used in breaking ties. Defaults to False.
        first_ac_bonus: The number of points to award if a solution gets AC on its first non-IE/CE run. Defaults to 10.
        time_bonus: Number of minutes to award an extra point for submitting before the contest end.
                    Specify 0 to disable. Defaults to 5.
    """

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
        score = 0
        format_data = {}

        submissions = participation.submissions.exclude(submission__result__in=('IE', 'CE'))

        submission_counts = {
            data['problem_id']: data['count'] for data in submissions.values('problem_id').annotate(count=Count('id'))
        }
        queryset = (
            submissions
            .values('problem_id')
            .filter(
                submission__date=Subquery(
                    submissions
                    .filter(problem_id=OuterRef('problem_id'))
                    .order_by('-submission__date')
                    .values('submission__date')[:1],
                ),
            )
            .annotate(points=Max('points'))
            .values_list('problem_id', 'problem__points', 'points', 'submission__date')
        )

        for problem_id, problem_points, points, date in queryset:
            sub_cnt = submission_counts.get(problem_id, 0)

            dt = (date - participation.start).total_seconds()

            bonus = 0
            if points > 0:
                # First AC bonus
                if sub_cnt == 1 and points == problem_points:
                    bonus += self.config['first_ac_bonus']
                # Time bonus
                if self.config['time_bonus']:
                    bonus += (participation.end_time - date).total_seconds() // 60 // self.config['time_bonus']

            format_data[str(problem_id)] = {'time': dt, 'points': points, 'bonus': bonus}

        for data in format_data.values():
            if self.config['cumtime']:
                cumtime += data['time']
            score += data['points'] + data['bonus']

        participation.cumtime = cumtime
        participation.score = round(score, self.contest.points_precision)
        participation.tiebreaker = 0
        participation.format_data = format_data
        participation.save()

    def display_user_problem(self, participation, contest_problem):
        format_data = (participation.format_data or {}).get(str(contest_problem.id))
        if format_data:
            bonus = format_html('<small> +{bonus}</small>',
                                bonus=floatformat(format_data['bonus'])) if format_data['bonus'] else ''

            return format_html(
                '<td class="{state}"><a href="{url}">{points}{bonus}<div class="solving-time">{time}</div></a></td>',
                state=(('pretest-' if self.contest.run_pretests_only and contest_problem.is_pretested else '') +
                       self.best_solution_state(format_data['points'], contest_problem.points)),
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
            '<td class="user-points"><a href="{url}">{points}<div class="solving-time">{cumtime}</div></a></td>',
            url=reverse('contest_all_user_submissions',
                        args=[self.contest.key, participation.user.user.username]),
            points=floatformat(participation.score, -self.contest.points_precision),
            cumtime=nice_repr(timedelta(seconds=participation.cumtime), 'noday') if self.config['cumtime'] else '',
        )

    def get_short_form_display(self):
        yield _('The score on your **last** non-CE submission for each problem will be used.')

        first_ac_bonus = self.config['first_ac_bonus']
        if first_ac_bonus:
            yield _(
                'There is a **%d bonus** for fully solving on your first non-CE submission.',
            ) % first_ac_bonus

        time_bonus = self.config['time_bonus']
        if time_bonus:
            yield ngettext(
                'For every **%d minute** you submit before the end of your window, there will be a **1** point bonus.',
                'For every **%d minutes** you submit before the end of your window, there will be a **1** point bonus.',
                time_bonus,
            ) % time_bonus

        if self.config['cumtime']:
            yield _('Ties will be broken by the sum of the last submission time on **all** problems.')
        else:
            yield _('Ties by score will **not** be broken.')
