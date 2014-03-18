import logging

from .judgehandler import JudgeHandler
from judge.models import Submission, SubmissionTestCase

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
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = 'G'
        submission.save()

    def on_grading_end(self, packet):
        JudgeHandler.on_grading_end(self, packet)
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
        test_case = SubmissionTestCase.objects.get_or_create(submission__id=packet['submission-id'],
                                                             case=packet['position'])[0]
        status = packet['status']
        if status & 2:
            test_case.status = 'RTE'
        elif status & 4:
            test_case.status = 'TLE'
        elif status & 1:
            test_case.status = 'WA'
        else:
            test_case.status = 'AC'
        test_case.time = packet['time']
        test_case.memory = packet['memory']
        test_case.points = packet['points']
        test_case.total = packet['total-points']
        test_case.save()
