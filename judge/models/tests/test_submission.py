from django.test import TestCase

from judge.models import ContestSubmission, Language, Submission
from judge.models.tests.util import CommonDataMixin, create_contest, create_contest_participation, \
    create_contest_problem, create_problem


class SubmissionTestCase(CommonDataMixin, TestCase):
    @classmethod
    def setUpTestData(self):
        super().setUpTestData()

        self.basic_submission = Submission.objects.create(
            user=self.profiles['normal'],
            problem=create_problem(code='basic'),
            language=Language.get_python3(),
            result='AC',
            status='D',
            case_points=99,
            case_total=100,
            memory=20,
        )

        self.ie_submission = Submission.objects.create(
            user=self.profiles['superuser'],
            problem=create_problem(
                code='ie',
                is_public=True,
            ),
            language=Language.get_python3(),
            result='IE',
            status='IE',
            memory=None,
        )

        # jump down the rabbit hole to attach a contest submission
        problem = create_problem(code='queued')
        contest = create_contest(key='queued')
        self.queued_submission = Submission.objects.create(
            user=self.profiles['superuser'],
            problem=problem,
            language=Language.get_python3(),
            contest_object=contest,
            case_points=50,
            case_total=100,
        )
        self.queued_contest_submission = ContestSubmission.objects.create(
            submission=self.queued_submission,
            problem=create_contest_problem(problem=problem, contest=contest, partial=False),
            participation=create_contest_participation(contest=contest, user='superuser'),
        )

    def test_basic_submission(self):
        self.assertEqual(self.basic_submission.result_class, '_AC')
        self.assertEqual(self.basic_submission.memory_bytes, 20 * 1024)
        self.assertEqual(self.basic_submission.short_status, 'AC')
        self.assertEqual(self.basic_submission.long_status, 'Accepted')
        self.assertTrue(self.basic_submission.is_graded)
        self.assertIsNone(self.basic_submission.contest_key)
        self.assertIsNone(self.basic_submission.contest_or_none)
        self.assertEqual(len(self.basic_submission.id_secret), 24)

    def test_ie_submission(self):
        self.assertEqual(self.ie_submission.result_class, 'IE')
        self.assertEqual(self.ie_submission.memory_bytes, 0)
        self.assertTrue(self.basic_submission.is_graded)

        self.ie_submission.update_contest()

    def test_queued_submission(self):
        self.assertIsNone(self.queued_submission.result_class)
        self.assertEqual(self.queued_submission.memory_bytes, 0)
        self.assertEqual(self.queued_submission.short_status, 'QU')
        self.assertEqual(self.queued_submission.long_status, 'Queued')
        self.assertFalse(self.queued_submission.is_graded)

        self.assertEqual(self.queued_submission.contest_key, 'queued')
        self.assertIsNotNone(self.queued_submission.contest_or_none)
        self.queued_contest_submission.points = -1000
        self.queued_submission.update_contest()
        self.assertEqual(self.queued_contest_submission.points, 0)

    def test_basic_submission_methods(self):
        data = {
            'superuser': {
                'can_see_detail': self.assertTrue,
            },
            'staff_problem_edit_own': {
                'can_see_detail': self.assertFalse,
            },
            'staff_problem_edit_all': {
                'can_see_detail': self.assertTrue,
            },
            'staff_problem_edit_public': {
                'can_see_detail': self.assertFalse,
            },
            'staff_problem_see_organization': {
                'can_see_detail': self.assertFalse,
            },
            'staff_submission_view_all': {
                'can_see_detail': self.assertTrue,
            },
            'normal': {
                'can_see_detail': self.assertTrue,
            },
            'anonymous': {
                'can_see_detail': self.assertFalse,
            },
        }
        self._test_object(self.basic_submission, data)

    def test_ie_submission_methods(self):
        data = {
            'staff_problem_edit_own': {
                'can_see_detail': self.assertFalse,
            },
            'staff_problem_edit_all': {
                'can_see_detail': self.assertTrue,
            },
            'staff_problem_edit_public': {
                'can_see_detail': self.assertTrue,
            },
            'staff_submission_view_all': {
                'can_see_detail': self.assertTrue,
            },
            'normal': {
                'can_see_detail': self.assertFalse,
            },
        }
        self._test_object(self.ie_submission, data)
