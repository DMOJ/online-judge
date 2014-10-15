import logging
from operator import itemgetter
from django.db.models import Min, Max
from django.utils import timezone
from judge.caching import update_submission, update_stats

from .judgehandler import JudgeHandler
from judge.models import Submission, SubmissionTestCase, Problem, Judge, Language
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
        return problem.time_limit, problem.memory_limit, problem.short_circuit

    def _authenticate(self, id, key):
        try:
            judge = Judge.objects.get(name=id)
        except Judge.DoesNotExist:
            return False
        return judge.auth_key == key

    def _connected(self):
        judge = Judge.objects.get(name=self.name)
        judge.last_connect = timezone.now()
        judge.online = True
        judge.problems = Problem.objects.filter(code__in=self.problems.keys())
        judge.runtimes = Language.objects.filter(key__in=self.executors)
        judge.save()

    def _disconnected(self):
        judge = Judge.objects.get(name=self.name)
        judge.online = False
        judge.save()

    def _update_ping(self):
        judge = Judge.objects.get(name=self.name)
        judge.ping = self.latency
        judge.load = self.load
        judge.save()

    def on_grading_begin(self, packet):
        JudgeHandler.on_grading_begin(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = 'G'
        submission.current_testcase = 1
        submission.save()
        event.post('sub_%d' % submission.id, {'type': 'grading-begin'})
        event.post('submissions', {'type': 'update-submission', 'id': submission.id})

    def _submission_is_batch(self, id):
        submission = Submission.objects.get(id=id)
        submission.batch = True
        submission.save()

    def on_grading_end(self, packet):
        JudgeHandler.on_grading_end(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])

        time = 0
        memory = 0
        points = 0.0
        total = 0
        status = 0
        status_codes = ['SC', 'AC', 'WA', 'MLE', 'TLE', 'IR', 'RTE', 'OLE']
        for case in SubmissionTestCase.objects.filter(submission=submission):
            time += case.time
            total += case.total
            points += case.points
            memory = max(memory, case.memory)
            i = status_codes.index(case.status)
            if i > status:
                status = i
        total = round(total, 1)

        if submission.batch:
            data = (SubmissionTestCase.objects.filter(submission_id=submission.id)
                    .values('batch').annotate(points=Min('points'), total=Max('total')))
            points = round(sum(map(itemgetter('points'), data)), 1)
            total = round(sum(map(itemgetter('total'), data)), 1)

        sub_points = round(points / total * submission.problem.points, 1)
        if not submission.problem.partial and sub_points != submission.problem.points:
            sub_points = 0

        submission.status = 'D'
        submission.time = time
        submission.memory = memory
        submission.points = sub_points
        submission.result = status_codes[status]
        submission.save()

        submission.user.calculate_points()

        if hasattr(submission, 'contest'):
            contest = submission.contest
            contest.points = round(points / total * contest.problem.points, 1)
            if not contest.problem.partial and contest.points != contest.problem.points:
                contest.points = 0
            contest.save()
            submission.contest.participation.recalculate_score()

        update_stats()

        event.post('sub_%d' % submission.id, {
            'type': 'grading-end',
            'time': time,
            'memory': memory,
            'points': float(points),
            'total': float(submission.problem.points),
            'result': submission.result
        })
        event.post('submissions', {'type': 'update-submission', 'id': submission.id})
        event.post('submissions', {'type': 'done-submission', 'id': submission.id})

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

    def on_submission_terminated(self, packet):
        JudgeHandler.on_submission_terminated(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        submission.status = submission.result = 'AB'
        submission.save()
        event.post('sub_%d' % submission.id, {
            'type': 'aborted-submission'
        })
        event.post('submissions', {'type': 'update-submission', 'id': submission.id})

    def on_test_case(self, packet):
        JudgeHandler.on_test_case(self, packet)
        submission = Submission.objects.get(id=packet['submission-id'])
        test_case = SubmissionTestCase(submission=submission, case=packet['position'])
        status = packet['status']
        if status & 4:
            test_case.status = 'TLE'
        elif status & 8:
            test_case.status = 'MLE'
        elif status & 64:
            test_case.status = 'OLE'
        elif status & 2:
            test_case.status = 'RTE'
        elif status & 16:
            test_case.status = 'IR'
        elif status & 1:
            test_case.status = 'WA'
        elif status & 32:
            test_case.status = 'SC'
        else:
            test_case.status = 'AC'
        test_case.time = packet['time']
        test_case.memory = packet['memory']
        test_case.points = packet['points']
        test_case.total = packet['total-points']
        test_case.batch = self.batch_id
        submission.current_testcase = packet['position'] + 1
        submission.save()
        test_case.save()
        event.post('sub_%d' % submission.id, {
            'type': 'test-case',
            'id': packet['position'],
            'status': test_case.status,
            'time': "%.3f" % round(float(packet['time']), 3),
            'memory': packet['memory'],
            'points': float(test_case.points),
            'total': float(test_case.total),
            'output': packet['output']
        })
        event.post('submissions', {'type': 'update-submission', 'id': submission.id})

    def on_supported_problems(self, packet):
        JudgeHandler.on_supported_problems(self, packet)

        judge = Judge.objects.get(name=self.name)
        judge.problems = Problem.objects.filter(code__in=self.problems.keys())
        judge.save()