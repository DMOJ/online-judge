import logging

from django.db import connection
from .judgehandler import JudgeHandler
from judge.models import Submission, SubmissionTestCase, Problem
from judge import event_poster as event

logger = logging.getLogger('judge.bridge')


class DjangoJudgeHandler(JudgeHandler):
    def finish(self):
        JudgeHandler.finish(self)
        if self._working:
            submission = Submission.objects.get(id=self._working)
            submission.status = 'IE'
            submission.save()

    def problem_data(self, problem):
        problem = Problem.objects.get(code=problem)
        params = dict(pair.split('=', 1) for pair in problem.grader_param.split(';')) if problem.grader_param else {}
        return problem.time_limit, problem.memory_limit, problem.short_circuit, problem.grader.key, params

    def on_grading_begin(self, packet):
        JudgeHandler.on_grading_begin(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = 'G'
        submission.save()
        event.post('sub_%d' % submission.id, {'type': 'grading-begin'})
        event.post('submissions', {'type': 'update-submission', 'id': submission.id})

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

        event.post('sub_%d' % submission.id, {
            'type': 'grading-end',
            'time': time,
            'memory': memory,
            'points': points,
            'total': submission.problem.points,
            'result': submission.result
        })
        event.post('submissions', {'type': 'update-submission', 'id': submission.id})
        connection.close()

    def on_compile_error(self, packet):
        JudgeHandler.on_compile_error(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = submission.result = 'CE'
        submission.error = packet['log']
        submission.save()
        event.post('sub_%d' % submission.id, {
            'type': 'compile-error',
            'log': packet['log']
        })
        event.post('submissions', {'type': 'update-submission', 'id': submission.id})
        connection.close()

    def on_bad_problem(self, packet):
        JudgeHandler.on_bad_problem(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = submission.result = 'IE'
        submission.save()
        event.post('sub_%d' % submission.id, {
            'type': 'bad-problem',
            'problem': packet['problem']
        })
        event.post('submissions', {'type': 'update-submission', 'id': submission.id})
        connection.close()

    def on_submission_terminated(self, packet):
        JudgeHandler.on_submission_terminated(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = submission.result = 'AB'
        submission.save()
        event.post('sub_%d' % submission.id, {
            'type': 'aborted-submission'
        })
        event.post('submissions', {'type': 'update-submission', 'id': submission.id})
        connection.close()

    def on_test_case(self, packet):
        JudgeHandler.on_test_case(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        test_case = SubmissionTestCase.objects.get_or_create(submission=submission, case=packet['position'])[0]
        status = packet['status']
        if status & 4:
            test_case.status = 'TLE'
        elif status & 8:
            test_case.status = 'MLE'
        elif status & 2:
            test_case.status = 'RTE'
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
        event.post('sub_%d' % submission.id, {
            'type': 'test-case',
            'id': packet['position'],
            'status': test_case.status,
            'time': "%.3f" % round(float(packet['time']), 3),
            'memory': packet['memory'],
            'points': test_case.points,
            'total': test_case.total,
            'output': packet['output']
        })
