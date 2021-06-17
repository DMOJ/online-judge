from operator import attrgetter

from judge.models import SubmissionSourceAccess
from . import registry


# TODO: maybe refactor this?
def get_editor_ids(contest):
    return set(map(attrgetter('id'), contest.authors.all())) | set(map(attrgetter('id'), contest.curators.all()))


@registry.function
def submission_layout(submission, profile_id, user, completed_problem_ids, editable_problem_ids, tester_problem_ids):
    problem_id = submission.problem_id
    submission_source_visibility = submission.problem.submission_source_visibility
    can_view = False
    can_edit = False

    if user.has_perm('judge.edit_all_problem') or problem_id in editable_problem_ids:
        can_view = True
        can_edit = True
    elif user.has_perm('judge.view_all_submission'):
        can_view = True
    elif profile_id == submission.user_id:
        can_view = True
    elif submission_source_visibility == SubmissionSourceAccess.ALWAYS:
        can_view = True
    elif submission.contest_object is not None and profile_id in get_editor_ids(submission.contest_object):
        can_view = True
    elif submission.problem_id in completed_problem_ids:
        can_view = submission.problem_id in tester_problem_ids
        if submission_source_visibility == SubmissionSourceAccess.SOLVED:
            can_view = can_view or submission.problem.is_public

    return can_view, can_edit
