from django.db import connection
from django.utils.translation import gettext_lazy

from judge.contest_format.ioi import IOIContestFormat
from judge.contest_format.registry import register_contest_format
from judge.timezone import from_database_time


@register_contest_format('ioi16')
class IOI16ContestFormat(IOIContestFormat):
    name = gettext_lazy('IOI16')
    config_defaults = {'cumtime': False}
    '''
        cumtime: Specify True if time penalties are to be computed. Defaults to False.
    '''

    def __init__(self, contest, config):
        super(IOI16ContestFormat, self).__init__(contest, config)

    def update_participation(self, participation):
        cumtime = 0
        score = 0
        format_data = {}

        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT *
                FROM (
                         SELECT q.prob,
                                q.date,
                                q.batch_points
                         FROM (
                                  SELECT cp.id          as `prob`,
                                         sub.id         as `subid`,
                                         sub.date       as `date`,
                                         tc.points      as `points`,
                                         tc.batch       as `batch`,
                                         Min(tc.points) as `batch_points`
                                  FROM judge_contestproblem cp
                                           INNER JOIN
                                       judge_contestsubmission cs
                                       ON (cs.problem_id = cp.id AND cs.participation_id = %s)
                                           LEFT OUTER JOIN
                                       judge_submission sub ON (sub.id = cs.submission_id)
                                           INNER JOIN judge_submissiontestcase tc
                                                      ON sub.id = tc.submission_id
                                  GROUP BY cp.id, tc.batch, sub.id
                              ) q
                                  INNER JOIN (
                             SELECT prob, batch, MAX(r.batch_points) max_batch_points
                             FROM (
                                      SELECT cp.id          as `prob`,
                                             tc.batch       as `batch`,
                                             Min(tc.points) as `batch_points`
                                      FROM judge_contestproblem cp
                                               INNER JOIN
                                           judge_contestsubmission cs
                                           ON (cs.problem_id = cp.id AND cs.participation_id = %s)
                                               INNER JOIN
                                           judge_submission sub ON (sub.id = cs.submission_id)
                                               INNER JOIN judge_submissiontestcase tc
                                                          ON sub.id = tc.submission_id
                                      GROUP BY cp.id, tc.batch, sub.id
                                  ) r
                             GROUP BY prob, batch
                         ) p
                                       ON p.prob = q.prob AND p.batch = q.batch
                         WHERE p.max_batch_points = q.batch_points
                           AND p.prob = q.prob
                         GROUP BY q.prob, q.batch
                     ) best
                ORDER BY best.date;
            ''', (participation.id, participation.id))

            for problem_id, time, subtask_points in cursor.fetchall():
                time = from_database_time(time)
                if self.config['cumtime']:
                    dt = (time - participation.start).total_seconds()
                else:
                    dt = 0

                if format_data.get(str(problem_id)) is None:
                    format_data[str(problem_id)] = {'points': 0, 'time': 0}
                format_data[str(problem_id)]['points'] += subtask_points
                format_data[str(problem_id)]['time'] = dt

            for problem_id in format_data:
                penalty = format_data[problem_id]['time']
                points = format_data[problem_id]['points']
                if self.config['cumtime'] and points:
                    cumtime += penalty
                score += points

        participation.cumtime = max(cumtime, 0)
        participation.score = score
        participation.tiebreaker = 0
        participation.format_data = format_data
        participation.save()
