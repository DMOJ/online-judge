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

        time = 0
        memory = 0
        points = 0.0
        total = 0
        status = 0
        status_codes = ['AC', 'WA', 'TLE', 'RTE']
        for case in SubmissionTestCase.objects.filter(submission=submission):
            time += case.time
            total += case.total
            points += case.points
            memory += case.memory
            i = status_codes.index(case.status)
            if i > status:
                status = i
        total = round(total, 1)
        points = round(points / total * submission.problem.points, 1)
        if not submission.problem.partial and points != total:
            points = 0

        submission.status = 'D'
        submission.time = time
        submission.memory = memory
        submission.points = points
        submission.result = status_codes[status]
        submission.save()

    def on_compile_error(self, packet):
        JudgeHandler.on_compile_error(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = 'CE'
        submission.save()

    def on_test_case(self, packet):
        JudgeHandler.on_test_case(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        test_case = SubmissionTestCase.objects.get_or_create(submission=submission, case=packet['position'])[0]
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
