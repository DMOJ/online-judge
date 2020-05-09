from . import registry


@registry.function
def submission_layout(submission, profile_id, user, completed_problem_ids, editable_problem_ids, tester_problem_ids):
    problem_id = submission.problem_id
    can_view = False
    can_edit = False

    if (user.has_perm('judge.edit_all_problem') and user.has_perm('judge.see_restricted_problem')) \
            or problem_id in editable_problem_ids:
        can_view = True
        can_edit = True
    elif profile_id == submission.user_id:
        can_view = True
    elif submission.problem_id in completed_problem_ids:
        can_view = submission.problem.is_public or submission.problem_id in tester_problem_ids
    elif user.has_perm('judge.view_all_submission'):
        if submission.problem.is_public:
            can_view = True
        elif user.has_perm('judge.see_restricted_problem') or not submission.problem.is_restricted:
            can_view = True

    return can_view, can_edit
