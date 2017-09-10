from collections import namedtuple

from django.conf import settings
from django.db import connection

from judge.models import Submission
from judge.timezone import from_database_time

PP_STEP = getattr(settings, 'PP_STEP', 0.95)
PP_ENTRIES = getattr(settings, 'PP_ENTRIES', 100)
PP_WEIGHT_TABLE = [pow(PP_STEP, i) for i in xrange(PP_ENTRIES)]

PPBreakdown = namedtuple('PPBreakdown', 'points weight scaled_points problem_name problem_code '
                                        'sub_id sub_date sub_points sub_total sub_result_class '
                                        'sub_short_status sub_long_status sub_lang')


def get_pp_breakdown(user, start=0, end=100):
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT max_points_table.problem_code,
                   max_points_table.problem_name,
                   max_points_table.max_points,
                   judge_submission.id,
                   judge_submission.date,
                   judge_submission.case_points,
                   judge_submission.case_total,
                   judge_submission.result,
                   judge_language.short_name,
                   judge_language.key
            FROM judge_submission
            JOIN (SELECT judge_problem.id problem_id,
                         judge_problem.name problem_name,
                         judge_problem.code problem_code,
                         MAX(judge_submission.points) AS max_points
                FROM judge_problem
                INNER JOIN judge_submission ON (judge_problem.id = judge_submission.problem_id)
                WHERE (judge_problem.is_public = True AND
                       judge_submission.points IS NOT NULL AND
                       judge_submission.user_id = %s)
                GROUP BY judge_problem.id
                HAVING MAX(judge_submission.points) > 0.0) AS max_points_table
            ON (judge_submission.problem_id = max_points_table.problem_id AND
                judge_submission.points = max_points_table.max_points AND
                judge_submission.user_id = %s)
            JOIN judge_language
            ON judge_submission.language_id = judge_language.id
            GROUP BY max_points_table.problem_id
            ORDER BY max_points DESC, judge_submission.date DESC
            LIMIT %s OFFSET %s
        ''', (user.id, user.id, end - start + 1, start))
        data = cursor.fetchall()

    breakdown = []
    for weight, contrib in zip(PP_WEIGHT_TABLE[start:end], data):
        code, name, points, id, date, case_points, case_total, result, lang_short_name, lang_key = contrib

        # Replicates a lot of the logic usually done on Submission objects
        lang_short_display_name = lang_short_name or lang_key
        result_class = Submission.result_class_from_code(result, case_points, case_total)
        long_status = Submission.USER_DISPLAY_CODES.get(result, '')

        breakdown.append(PPBreakdown(
            points=points,
            weight=weight * 100,
            scaled_points=points * weight,
            problem_name=name,
            problem_code=code,
            sub_id=id,
            sub_date=from_database_time(date),
            sub_points=case_points,
            sub_total=case_total,
            sub_short_status=result,
            sub_long_status=long_status,
            sub_result_class=result_class,
            sub_lang=lang_short_display_name,
        ))
    has_more = end < min(len(PP_WEIGHT_TABLE), start + len(data))
    return breakdown, has_more
