from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Max
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from judge.contest_format.base import BaseContestFormat
from judge.contest_format.registry import register_contest_format
from judge.utils.timedelta import nice_repr


@register_contest_format('default')
class DefaultContestFormat(BaseContestFormat):
    name = gettext_lazy('Default')

    @classmethod
    def validate(cls, config):
        if config is not None and (not isinstance(config, dict) or config):
            raise ValidationError('default contest expects no config or empty dict as config')

    def __init__(self, contest, config):
        super(DefaultContestFormat, self).__init__(contest, config)

    def update_participation(self, participation):
        cumtime = 0
        points = 0
        format_data = {}

        for result in participation.submissions.values('problem_id').annotate(
                time=Max('submission__date'), points=Max('points'),
        ):
            dt = (result['time'] - participation.start).total_seconds()
            if result['points']:
                cumtime += dt
            format_data[str(result['problem_id'])] = {'time': dt, 'points': result['points']}
            points += result['points']

        participation.cumtime = max(cumtime, 0)
        participation.score = points
        participation.tiebreaker = 0
        participation.format_data = format_data
        participation.save()

    def display_user_problem(self, participation, contest_problem):
        format_data = (participation.format_data or {}).get(str(contest_problem.id))
        if format_data:
            return format_html(
                u'<td class="{state}"><a href="{url}">{points}<div class="solving-time">{time}</div></a></td>',
                state=(('pretest-' if self.contest.run_pretests_only and contest_problem.is_pretested else '') +
                       self.best_solution_state(format_data['points'], contest_problem.points)),
                url=reverse('contest_user_submissions',
                            args=[self.contest.key, participation.user.user.username, contest_problem.problem.code]),
                points=floatformat(format_data['points']),
                time=nice_repr(timedelta(seconds=format_data['time']), 'noday'),
            )
        else:
            return mark_safe('<td></td>')

    def display_participation_result(self, participation):
        return format_html(
            u'<td class="user-points">{points}<div class="solving-time">{cumtime}</div></td>',
            points=floatformat(participation.score),
            cumtime=nice_repr(timedelta(seconds=participation.cumtime), 'noday'),
        )

    def get_problem_breakdown(self, participation, contest_problems):
        return [(participation.format_data or {}).get(str(contest_problem.id)) for contest_problem in contest_problems]

    def get_label_for_problem(self, index):
        return str(index + 1)
