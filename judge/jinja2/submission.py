from . import registry


@registry.function
def submission_layout(submission, profile_id, user, completed_problem_ids, editable_problem_ids, tester_problem_ids):
    problem_id = submission.problem_id
    can_view = False

    if user.has_perm('judge.view_all_submission'):
        can_view = True

    if profile_id == submission.user_id:
        can_view = True

    if problem_id in editable_problem_ids:
        can_view = True

    if submission.problem_id in completed_problem_ids:
        can_view |= submission.problem.is_public or submission.problem_id in tester_problem_ids

    return can_view
