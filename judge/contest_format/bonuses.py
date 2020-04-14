from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import ExpressionWrapper, F, FloatField, Max, Min, OuterRef, Subquery
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from judge.contest_format.default import DefaultContestFormat
from judge.contest_format.registry import register_contest_format
from judge.utils.timedelta import nice_repr


@register_contest_format('bonuses')
class BonusesContestFormat(DefaultContestFormat):
    name = gettext_lazy('Bonuses')
    config_defaults = {
        'time_bonus': 0,
        'first_submission_bonus': 0,
    }
    """
        time_bonus: Number of minutes to award an extra point for submitting before the contest end.
        first_submission_bonus: Bonus points for fully solving on first submission.
    """

    @classmethod
    def validate(cls, config):
        if not isinstance(config, dict):
            raise ValidationError('bonuses contest expects a dict as config')
        for key in config.keys():
            if key not in cls.config_defaults:
                raise ValidationError('unknown config key "%s"' % key)

    def __init__(self, contest, config):
        super().__init__(contest, self.config_defaults.copy())
        self.config.update(config)

    def update_participation(self, participation):
        cumtime = 0
        score = 0
        format_data = {}

        total_wrapper = ExpressionWrapper(F('points') + F('bonus'), output_field=FloatField())
        queryset = (participation.submissions.values('problem_id').annotate(total=total_wrapper)
                                             .filter(total=Subquery(
                                                 participation.submissions.filter(problem_id=OuterRef('problem_id'))
                                                                          .annotate(best=total_wrapper)
                                                                          .order_by('-best').values('best')[:1]))
                                             .annotate(time=Min('submission__date'), points=Max('points'))
                                             .values_list('problem_id', 'time', 'points', 'total'))

        for problem_id, time, points, total in queryset:
            dt = (time - participation.start).total_seconds()
            if total:
                score += total
                cumtime += dt
            format_data[str(problem_id)] = {
                'points': points,
                'bonus': total - points,
                'time': dt,
            }

        queryset = (participation.submissions.values('problem_id', 'problem__points')
                                             .filter(submission__date=Subquery(
                                                 participation.submissions.filter(problem_id=OuterRef('problem_id'))
                                                                          .order_by('submission__date')
                                                                          .values('submission__date')[:1]))
                                             .annotate(points=Max('points'))
                                             .values_list('problem_id', 'points', 'problem__points'))

        for problem_id, points, problem_points in queryset:
            format_data[str(problem_id)].update({
                'first_solve': points == problem_points,
            })

        participation.cumtime = max(cumtime, 0)
        participation.score = score
        participation.tiebreaker = 0
        participation.format_data = format_data
        participation.save()

    def display_user_problem(self, participation, contest_problem):
        format_data = (participation.format_data or {}).get(str(contest_problem.id))
        if format_data:
            pretest = ('pretest-' if self.contest.run_pretests_only and contest_problem.is_pretested else '')
            first_solve = (' first-solve' if format_data['first_solve'] else '')
            bonus = format_html(
                '<font style="font-size:10px;"> +{bonus}</font>',
                bonus=floatformat(format_data['bonus']),
            ) if format_data['bonus'] else ''

            return format_html(
                '<td class="{state}"><a href="{url}">{points}{bonus}<div class="solving-time">{time}</div></a></td>',
                state=pretest + self.best_solution_state(format_data['points'], contest_problem.points) + first_solve,
                url=reverse('contest_user_submissions',
                            args=[self.contest.key, participation.user.user.username, contest_problem.problem.code]),
                points=floatformat(format_data['points']),
                bonus=bonus,
                time=nice_repr(timedelta(seconds=format_data['time']), 'noday'),
            )
        else:
            return mark_safe('<td></td>')
