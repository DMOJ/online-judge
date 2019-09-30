from . import registry


@registry.function
def submission_layout(submission, profile_id, user, editable_problem_ids, completed_problem_ids):
    problem_id = submission.problem_id
    can_view = False

    if problem_id in editable_problem_ids:
        can_view = True

    if profile_id == submission.user_id:
        can_view = True

    if user.has_perm('judge.change_submission'):
        can_view = True

    if submission.problem_id in completed_problem_ids:
        can_view |= submission.problem.is_public or profile_id in submission.problem.tester_ids

    return can_view
