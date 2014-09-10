import logging

from .judgehandler import JudgeHandler
from judge.models import Submission, SubmissionTestCase
from judge.simple_comet_client import send_message

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
        send_message('sub_%d' % submission.id, 'grading-begin')
        send_message('submissions', 'submission-status %d %s' % (submission.id, submission.status))

    def on_grading_end(self, packet):
        JudgeHandler.on_grading_end(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])

        time = 0
        memory = 0
        points = 0.0
        total = 0
        status = 0
        status_codes = ['AC', 'WA', 'MLE', 'TLE', 'IR', 'RTE']
        for case in SubmissionTestCase.objects.filter(submission=submission):
            time += case.time
            total += case.total
            points += case.points
            memory = max(memory, case.memory)
            i = status_codes.index(case.status)
            if i > status:
                status = i
        total = round(total, 1)
        points = round(points / total * submission.problem.points, 1)
        if not submission.problem.partial and points != submission.problem.points:
            points = 0

        submission.status = 'D'
        submission.time = time
        submission.memory = memory
        submission.points = points
        submission.result = status_codes[status]
        submission.save()

        submission.user.calculate_points()

        send_message('sub_%d' % submission.id,
                     'grading-end %.3f %d %.1f %.1f %s' % (time, memory, points, submission.problem.points,
                                                           submission.result))
        send_message('submissions', 'submission-end %d %.3f %d %.1f %.1f %s' % (
            submission.id, time, memory, points, submission.problem.points,
            submission.result))

    def on_compile_error(self, packet):
        JudgeHandler.on_compile_error(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = submission.result = 'CE'
        submission.save()
        send_message('sub_%d' % submission.id, 'compile-error %s' % packet['log'].replace(" ", "\f"))
        send_message('submissions', 'submission-status %d %s' % (submission.id, submission.status))

    def on_bad_problem(self, packet):
        JudgeHandler.on_bad_problem(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = submission.result = 'IE'
        submission.save()
        send_message('sub_%d' % submission.id, 'bad-problem %s' % packet['problem'])
        send_message('submissions', 'submission-status %d %s' % (submission.id, submission.status))

    def on_submission_terminated(self, packet):
        JudgeHandler.on_submission_terminated(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = submission.result = 'AB'
        submission.save()
        send_message('submissions', 'submission-status %d %s' % (submission.id, submission.status))

    def on_test_case(self, packet):
        JudgeHandler.on_test_case(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        test_case = SubmissionTestCase.objects.get_or_create(submission=submission, case=packet['position'])[0]
        status = packet['status']
        if status & 2:
            test_case.status = 'RTE'
        elif status & 4:
            test_case.status = 'TLE'
        elif status & 8:
            test_case.status = 'MLE'
        elif status & 16:
            test_case.status = 'IR'
        elif status & 1:
            test_case.status = 'WA'
        else:
            test_case.status = 'AC'
        test_case.time = packet['time']
        test_case.memory = packet['memory']
        test_case.points = packet['points']
        test_case.total = packet['total-points']
        test_case.save()
        chan = 'sub_%d' % submission.id
        send_message(chan, 'test-case %d %s %.3f %d %.1f %.1f (%s)' % (packet['position'], test_case.status,
                                                                       packet['time'], packet['memory'],
                                                                       float(test_case.points), float(test_case.total),
                                                                       packet['output']))
