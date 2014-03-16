import logging

from .judgehandler import JudgeHandler
from judge.models import Submission, SubmissionTestCase, TestCase

logger = logging.getLogger('judge.bridge')


class DjangoJudgeHandler(JudgeHandler):
    def finish(self):
        JudgeHandler.finish(self)
        for id in self._load:
            submission = Submission.objects.get(id=id)
            submission.status = 'IE'
            submission.save()

    def on_grading_begin(self, packet):
        JudgeHandler.on_grading_begin(self, packet)
        JudgeHandler.on_compile_error(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = 'G'
        submission.save()

    def on_grading_end(self, packet):
        JudgeHandler.on_grading_end(self, packet)
        JudgeHandler.on_compile_error(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = 'D'
        submission.save()

    def on_compile_error(self, packet):
        JudgeHandler.on_compile_error(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = 'CE'
        submission.save()

    def on_test_case(self, packet):
        JudgeHandler.on_test_case(self, packet)
        test_case = SubmissionTestCase.objects.get(submission__id=packet['submission-id'],
                                                   test_case__id=packet['case-id'])
        test_case.status = packet['status']
        test_case.time = packet['time']
        test_case.memory = packet['memory']
        test_case.points = packet['points']
        test_case.save()
