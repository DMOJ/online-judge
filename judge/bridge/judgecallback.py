import logging
from django import db
from django.utils import timezone
from judge.caching import finished_submission

from .judgehandler import JudgeHandler
from judge.models import Submission, SubmissionTestCase, Problem, Judge, Language, LanguageLimit
from judge import event_poster as event

logger = logging.getLogger('judge.bridge')


def _ensure_connection():
    try:
        db.connection.cursor().execute('SELECT 1').fetchall()
    except Exception:
        db.connection.close()


class DjangoJudgeHandler(JudgeHandler):
    def on_close(self):
        super(DjangoJudgeHandler, self).on_close()
        if self._working:
            submission = Submission.objects.get(id=self._working)
            submission.status = 'IE'
            submission.save()

    def problem_data(self, problem, language):
        _ensure_connection()  # We are called from the django-facing daemon thread. Guess what happens.
        problem = Problem.objects.get(code=problem)
        time, memory = problem.time_limit, problem.memory_limit
        try:
            limit = LanguageLimit.objects.get(problem=problem, language__key=language)
        except LanguageLimit.DoesNotExist:
            pass
        else:
            time, memory = limit.time_limit, limit.memory_limit
        return time, memory, problem.short_circuit

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
        Judge.objects.filter(name=self.name).update(online=False)

    def _update_ping(self):
        try:
            Judge.objects.filter(name=self.name).update(ping=self.latency, load=self.load)
        except Exception as e:
            # What can I do? I don't want to tie this to MySQL.
            if e.__class__.__name__ == 'OperationalError' and e.__module__ == '_mysql_exceptions' and e.args[0] == 2006:
                db.close_connection()

    def on_submission_processing(self, packet):
        try:
            submission = Submission.objects.get(id=packet['submission-id'])
        except Submission.DoesNotExist:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            return
        submission.status = 'P'
        submission.save()
        event.post('sub_%d' % submission.id, {'type': 'processing'})
        if not submission.problem.is_public:
            return
        event.post('submissions', {'type': 'update-submission', 'id': submission.id,
                                   'state': 'processing', 'contest': submission.contest_key,
                                   'user': submission.user_id, 'problem': submission.problem_id})

    def on_grading_begin(self, packet):
        super(DjangoJudgeHandler, self).on_grading_begin(packet)
        try:
            submission = Submission.objects.get(id=packet['submission-id'])
        except Submission.DoesNotExist:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            return
        submission.status = 'G'
        submission.current_testcase = 1
        submission.batch = False
        submission.save()
        SubmissionTestCase.objects.filter(submission_id=submission.id).delete()
        event.post('sub_%d' % submission.id, {'type': 'grading-begin'})
        if not submission.problem.is_public:
            return
        event.post('submissions', {'type': 'update-submission', 'id': submission.id,
                                   'state': 'grading-begin', 'contest': submission.contest_key,
                                   'user': submission.user_id, 'problem': submission.problem_id})

    def _submission_is_batch(self, id):
        submission = Submission.objects.get(id=id)
        submission.batch = True
        submission.save()

    def on_grading_end(self, packet):
        super(DjangoJudgeHandler, self).on_grading_end(packet)
        try:
            submission = Submission.objects.get(id=packet['submission-id'])
        except Submission.DoesNotExist:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            return

        time = 0
        memory = 0
        points = 0.0
        total = 0
        status = 0
        status_codes = ['SC', 'AC', 'WA', 'MLE', 'TLE', 'IR', 'RTE', 'OLE']
        batches = {}  # batch number: (points, total)

        for case in SubmissionTestCase.objects.filter(submission=submission):
            time += case.time
            if not case.batch:
                points += case.points
                total += case.total
            else:
                if case.batch in batches:
                    batches[case.batch][0] = min(batches[case.batch][0], case.points)
                    batches[case.batch][1] = max(batches[case.batch][1], case.total)
                else:
                    batches[case.batch] = [case.points, case.total]
            memory = max(memory, case.memory)
            i = status_codes.index(case.status)
            if i > status:
                status = i

        for i in batches:
            points += batches[i][0]
            total += batches[i][1]

        points = round(points, 1)
        total = round(total, 1)
        submission.case_points = points
        submission.case_total = total

        sub_points = round(points / total * submission.problem.points if total > 0 else 0, 1)
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
            contest.points = round(points / total * contest.problem.points if total > 0 else 0, 1)
            if not contest.problem.partial and contest.points != contest.problem.points:
                contest.points = 0
            contest.save()
            submission.contest.participation.recalculate_score()
            submission.contest.participation.update_cumtime()

        finished_submission(submission)

        event.post('sub_%d' % submission.id, {
            'type': 'grading-end',
            'time': time,
            'memory': memory,
            'points': float(points),
            'total': float(submission.problem.points),
            'result': submission.result
        })
        if hasattr(submission, 'contest'):
            participation = submission.contest.participation
            event.post('contest_%d' % participation.contest_id, {'type': 'update'})
        if not submission.problem.is_public:
            return
        event.post('submissions', {'type': 'update-submission', 'id': submission.id,
                                   'state': 'grading-end', 'contest': submission.contest_key,
                                   'user': submission.user_id, 'problem': submission.problem_id})
        event.post('submissions', {'type': 'done-submission', 'id': submission.id,
                                   'contest': submission.contest_key,
                                   'user': submission.user_id, 'problem': submission.problem_id})

    def on_compile_error(self, packet):
        super(DjangoJudgeHandler, self).on_compile_error(packet)
        try:
            submission = Submission.objects.get(id=packet['submission-id'])
        except Submission.DoesNotExist:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            return
        submission.status = submission.result = 'CE'
        submission.error = packet['log']
        submission.save()
        event.post('sub_%d' % submission.id, {
            'type': 'compile-error',
            'log': packet['log']
        })
        if not submission.problem.is_public:
            return
        event.post('submissions', {'type': 'update-submission', 'id': submission.id,
                                   'state': 'compile-error', 'contest': submission.contest_key,
                                   'user': submission.user_id, 'problem': submission.problem_id})

    def on_compile_message(self, packet):
        super(DjangoJudgeHandler, self).on_compile_message(packet)
        try:
            submission = Submission.objects.get(id=packet['submission-id'])
        except Submission.DoesNotExist:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            return
        submission.error = packet['log']
        submission.save()
        event.post('sub_%d' % submission.id, {
            'type': 'compile-message'
        })

    def on_bad_problem(self, packet):
        super(DjangoJudgeHandler, self).on_bad_problem(packet)
        try:
            submission = Submission.objects.get(id=packet['submission-id'])
        except Submission.DoesNotExist:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            return
        submission.status = submission.result = 'IE'
        submission.save()
        event.post('sub_%d' % submission.id, {
            'type': 'internal-error'
        })
        if not submission.problem.is_public:
            return
        event.post('submissions', {'type': 'update-submission', 'id': submission.id,
                                   'state': 'internal-error', 'contest': submission.contest_key,
                                   'user': submission.user_id, 'problem': submission.problem_id})

    def on_submission_terminated(self, packet):
        super(DjangoJudgeHandler, self).on_submission_terminated(packet)
        try:
            submission = Submission.objects.get(id=packet['submission-id'])
        except Submission.DoesNotExist:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            return
        submission.status = submission.result = 'AB'
        submission.save()
        if not submission.problem.is_public:
            return
        event.post('sub_%d' % submission.id, {
            'type': 'aborted-submission'
        })
        event.post('submissions', {'type': 'update-submission', 'id': submission.id,
                                   'state': 'terminated', 'contest': submission.contest_key,
                                   'user': submission.user_id, 'problem': submission.problem_id})

    def on_test_case(self, packet):
        super(DjangoJudgeHandler, self).on_test_case(packet)
        try:
            submission = Submission.objects.get(id=packet['submission-id'])
        except Submission.DoesNotExist:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            return
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
        test_case.batch = self.batch_id if self.in_batch else None
        test_case.feedback = packet.get('feedback', None) or ''
        test_case.output = packet['output']
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
        if not submission.problem.is_public:
            return
        event.post('submissions', {'type': 'update-submission', 'id': submission.id,
                                   'state': 'test-case', 'contest': submission.contest_key,
                                   'user': submission.user_id, 'problem': submission.problem_id})

    def on_supported_problems(self, packet):
        super(DjangoJudgeHandler, self).on_supported_problems(packet)

        judge = Judge.objects.get(name=self.name)
        judge.problems = Problem.objects.filter(code__in=self.problems.keys())
        judge.save()
