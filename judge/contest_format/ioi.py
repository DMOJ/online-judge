from collections import defaultdict

from django.db.models import Case, CharField, F, Min, Value, When, Window
from django.db.models.functions import Cast, Concat, RowNumber
from django.utils.translation import gettext as _, gettext_lazy

from judge.contest_format.legacy_ioi import LegacyIOIContestFormat
from judge.contest_format.registry import register_contest_format


@register_contest_format('ioi16')
class IOIContestFormat(LegacyIOIContestFormat):
    name = gettext_lazy('IOI')
    config_defaults = {'cumtime': False}
    """
        cumtime: Specify True if time penalties are to be computed. Defaults to False.
    """

    def update_participation(self, participation):
        cumtime = 0
        score = 0
        format_data = {}

        # Compute one row per submission/subtask. Batched cases are grouped by
        # batch number; unbatched cases are intentionally grouped by case number
        # so that NULL batches do not collapse into one fake subtask.
        subtask_attempts = (
            participation.submissions
            .filter(
                submission__status='D',
                submission__test_cases__points__isnull=False,
                submission__test_cases__total__gt=0,
            )
            .annotate(
                subtask=Case(
                    When(
                        submission__test_cases__batch__isnull=True,
                        then=Concat(
                            Value('case:'),
                            Cast('submission__test_cases__case', output_field=CharField()),
                            output_field=CharField(),
                        ),
                    ),
                    default=Concat(
                        Value('batch:'),
                        Cast('submission__test_cases__batch', output_field=CharField()),
                        output_field=CharField(),
                    ),
                    output_field=CharField(),
                ),
            )
            .values(
                'problem_id',
                'problem__points',
                'submission_id',
                'submission__date',
                'subtask',
            )
            .annotate(
                points=Min('submission__test_cases__points'),
                total=Min('submission__test_cases__total'),
            )
            .annotate(
                rank=Window(
                    expression=RowNumber(),
                    partition_by=[F('problem_id'), F('subtask')],
                    order_by=[
                        F('points').desc(),
                        F('submission__date').asc(),
                        F('submission_id').asc(),
                    ],
                ),
            )
            .filter(rank=1)
            .order_by()
        )

        problems = defaultdict(lambda: {
            'raw_points': 0,
            'raw_total': 0,
            'contest_points': 0,
            'time': 0,
        })

        for subtask in subtask_attempts:
            problem = problems[str(subtask['problem_id'])]

            problem['contest_points'] = subtask['problem__points']
            problem['raw_points'] += subtask['points'] or 0
            problem['raw_total'] += subtask['total'] or 0

            if self.config['cumtime'] and subtask['points']:
                dt = (subtask['submission__date'] - participation.start).total_seconds()
                problem['time'] = max(problem['time'], dt)

        for problem_id, problem in problems.items():
            if problem['raw_total']:
                points = problem['raw_points'] / problem['raw_total'] * problem['contest_points']
            else:
                points = 0

            penalty = max(problem['time'], 0) if points else 0
            format_data[problem_id] = {'points': points, 'time': penalty}

            if self.config['cumtime'] and points:
                cumtime += penalty
            score += points

        participation.cumtime = max(cumtime, 0)
        participation.score = round(score, self.contest.points_precision)
        participation.tiebreaker = 0
        participation.format_data = format_data
        participation.save()

    def get_short_form_display(self):
        yield _('The maximum score for each problem batch will be used.')

        if self.config['cumtime']:
            yield _('Ties will be broken by the sum of the last score altering submission time on problems with a '
                    'non-zero score.')
        else:
            yield _('Ties by score will **not** be broken.')
