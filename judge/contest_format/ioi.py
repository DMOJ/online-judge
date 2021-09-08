from django.db import connection
from django.utils.translation import gettext as _, gettext_lazy

from judge.contest_format.legacy_ioi import LegacyIOIContestFormat
from judge.contest_format.registry import register_contest_format
from judge.timezone import from_database_time


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

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT q.prob,
                       MIN(q.date) as `date`,
                       q.batch_points
                FROM (
                         SELECT cp.id          as `prob`,
                                sub.id         as `subid`,
                                sub.date       as `date`,
                                tc.points      as `points`,
                                tc.batch       as `batch`,
                                MIN(tc.points) as `batch_points`
                         FROM judge_contestproblem cp
                                  INNER JOIN
                              judge_contestsubmission cs
                              ON (cs.problem_id = cp.id AND cs.participation_id = %s)
                                  LEFT OUTER JOIN
                              judge_submission sub
                              ON (sub.id = cs.submission_id AND sub.status = 'D')
                                  INNER JOIN judge_submissiontestcase tc
                              ON sub.id = tc.submission_id
                         GROUP BY cp.id, tc.batch, sub.id
                     ) q
                         INNER JOIN (
                    SELECT prob, batch, MAX(r.batch_points) as max_batch_points
                    FROM (
                             SELECT cp.id          as `prob`,
                                    tc.batch       as `batch`,
                                    MIN(tc.points) as `batch_points`
                             FROM judge_contestproblem cp
                                      INNER JOIN
                                  judge_contestsubmission cs
                                  ON (cs.problem_id = cp.id AND cs.participation_id = %s)
                                      LEFT OUTER JOIN
                                  judge_submission sub
                                  ON (sub.id = cs.submission_id AND sub.status = 'D')
                                      INNER JOIN judge_submissiontestcase tc
                                  ON sub.id = tc.submission_id
                             GROUP BY cp.id, tc.batch, sub.id
                         ) r
                    GROUP BY prob, batch
                ) p
                ON p.prob = q.prob AND (p.batch = q.batch OR p.batch is NULL AND q.batch is NULL)
                WHERE p.max_batch_points = q.batch_points
                GROUP BY q.prob, q.batch
            """, (participation.id, participation.id))

            for problem_id, time, subtask_points in cursor.fetchall():
                problem_id = str(problem_id)
                time = from_database_time(time)
                if self.config['cumtime']:
                    dt = (time - participation.start).total_seconds()
                else:
                    dt = 0

                if format_data.get(problem_id) is None:
                    format_data[problem_id] = {'points': 0, 'time': 0}
                format_data[problem_id]['points'] += subtask_points
                format_data[problem_id]['time'] = max(dt, format_data[problem_id]['time'])

            for problem_data in format_data.values():
                penalty = problem_data['time']
                points = problem_data['points']
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
