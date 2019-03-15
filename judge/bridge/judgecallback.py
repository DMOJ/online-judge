import json
import logging
import os
import time

from django import db
from django.utils import timezone

from judge import event_poster as event
from judge.caching import finished_submission
from judge.models import Submission, SubmissionTestCase, Problem, Judge, Language, LanguageLimit, RuntimeVersion
from .judgehandler import JudgeHandler

logger = logging.getLogger('judge.bridge')
json_log = logging.getLogger('judge.json.bridge')

UPDATE_RATE_LIMIT = 5
UPDATE_RATE_TIME = 0.5
TIMER = [time.time, time.clock][os.name == 'nt']


def _ensure_connection():
    try:
        db.connection.cursor().execute('SELECT 1').fetchall()
    except Exception:
        db.connection.close()


class DjangoJudgeHandler(JudgeHandler):
    def __init__(self, server, socket):
        super(DjangoJudgeHandler, self).__init__(server, socket)

        # each value is (updates, last reset)
        self.update_counter = {}
        self.judge = None
        self.judge_address = None

        self._submission_cache_id = None
        self._submission_cache = {}

        json_log.info(self._make_json_log(action='connect'))

    def on_close(self):
        super(DjangoJudgeHandler, self).on_close()
        json_log.info(self._make_json_log(action='disconnect', info='judge disconnected'))
        if self._working:
            Submission.objects.filter(id=self._working).update(status='IE')
            json_log.error(self._make_json_log(sub=self._working, action='close', info='IE due to shutdown on grading'))

    def on_malformed(self, packet):
        super(DjangoJudgeHandler, self).on_malformed(packet)
        json_log.exception(self._make_json_log(sub=self._working, info='malformed zlib packet'))

    def _packet_exception(self):
        json_log.exception(self._make_json_log(sub=self._working, info='packet processing exception'))

    def get_related_submission_data(self, submission):
        _ensure_connection()  # We are called from the django-facing daemon thread. Guess what happens.

        try:
            pid, time, memory, short_circuit, lid, is_pretested = (
                Submission.objects.filter(id=submission)
                          .values_list('problem__id', 'problem__time_limit', 'problem__memory_limit',
                                       'problem__short_circuit', 'language__id', 'is_pretested')).get()
        except Submission.DoesNotExist:
            logger.error('Submission vanished: %d', submission)
            json_log.error(self._make_json_log(
                sub=self._working, action='request',
                info='submission vanished when fetching info'
            ))
            return

        try:
            time, memory = (LanguageLimit.objects.filter(problem__id=pid, language__id=lid)
                                         .values_list('time_limit', 'memory_limit').get())
        except LanguageLimit.DoesNotExist:
            pass
        return time, memory, short_circuit, is_pretested

    def _authenticate(self, id, key):
        result = Judge.objects.filter(name=id, auth_key=key, is_blocked=False).exists()
        if not result:
            json_log.warning(self._make_json_log(action='auth', judge=id, info='judge failed authentication'))
        return result

    def _connected(self):
        judge = self.judge = Judge.objects.get(name=self.name)
        judge.start_time = timezone.now()
        judge.online = True
        judge.problems.set(Problem.objects.filter(code__in=self.problems.keys()))
        judge.runtimes.set(Language.objects.filter(key__in=self.executors.keys()))

        # Delete now in case we somehow crashed and left some over from the last connection
        RuntimeVersion.objects.filter(judge=judge).delete()
        versions = []
        for lang in judge.runtimes.all():
            versions += [
                RuntimeVersion(language=lang, name=name, version='.'.join(map(str, version)), priority=idx, judge=judge)
                for idx, (name, version) in enumerate(self.executors[lang.key])
            ]
        RuntimeVersion.objects.bulk_create(versions)
        judge.last_ip = self.client_address[0]
        judge.save()
        self.judge_address = '[%s]:%s' % (self.client_address[0], self.client_address[1])
        json_log.info(self._make_json_log(action='auth', info='judge successfully authenticated',
                                          executors=self.executors.keys()))

    def _disconnected(self):
        Judge.objects.filter(id=self.judge.id).update(online=False)
        RuntimeVersion.objects.filter(judge=self.judge).delete()

    def _update_ping(self):
        try:
            Judge.objects.filter(name=self.name).update(ping=self.latency, load=self.load)
        except Exception as e:
            # What can I do? I don't want to tie this to MySQL.
            if e.__class__.__name__ == 'OperationalError' and e.__module__ == '_mysql_exceptions' and e.args[0] == 2006:
                db.connection.close()

    def _post_update_submission(self, id, state, done=False):
        if self._submission_cache_id == id:
            data = self._submission_cache
        else:
            self._submission_cache = data = Submission.objects.filter(id=id).values(
                'problem__is_public', 'contest__participation__contest__key',
                'user_id', 'problem_id', 'status', 'language__key'
            ).get()
            self._submission_cache_id = id

        if data['problem__is_public']:
            event.post('submissions', {
                'type': 'done-submission' if done else 'update-submission',
                'state': state, 'id': id,
                'contest': data['contest__participation__contest__key'],
                'user': data['user_id'], 'problem': data['problem_id'],
                'status': data['status'], 'language': data['language__key'],
            })

    def on_submission_processing(self, packet):
        id = packet['submission-id']
        if Submission.objects.filter(id=id).update(status='P', judged_on=self.judge):
            event.post('sub_%s' % Submission.get_id_secret(id), {'type': 'processing'})
            self._post_update_submission(id, 'processing')
            json_log.info(self._make_json_log(packet, action='processing'))
        else:
            logger.warning('Unknown submission: %d', id)
            json_log.error(self._make_json_log(packet, action='processing', info='unknown submission'))

    def on_submission_wrong_acknowledge(self, packet, expected, got):
        json_log.error(self._make_json_log(packet, action='processing', info='wrong-acknowledge', expected=expected))

    def on_grading_begin(self, packet):
        super(DjangoJudgeHandler, self).on_grading_begin(packet)
        if Submission.objects.filter(id=packet['submission-id']).update(
                status='G', is_pretested=packet['pretested'],
                current_testcase=1, batch=False):
            SubmissionTestCase.objects.filter(submission_id=packet['submission-id']).delete()
            event.post('sub_%s' % Submission.get_id_secret(packet['submission-id']), {'type': 'grading-begin'})
            self._post_update_submission(packet['submission-id'], 'grading-begin')
            json_log.info(self._make_json_log(packet, action='grading-begin'))
        else:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            json_log.error(self._make_json_log(packet, action='grading-begin', info='unknown submission'))

    def _submission_is_batch(self, id):
        if not Submission.objects.filter(id=id).update(batch=True):
            logger.warning('Unknown submission: %d', id)

    def on_grading_end(self, packet):
        super(DjangoJudgeHandler, self).on_grading_end(packet)

        try:
            submission = Submission.objects.get(id=packet['submission-id'])
        except Submission.DoesNotExist:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            json_log.error(self._make_json_log(packet, action='grading-end', info='unknown submission'))
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

        problem = submission.problem
        sub_points = round(points / total * problem.points if total > 0 else 0, 3)
        if not problem.partial and sub_points != problem.points:
            sub_points = 0

        submission.status = 'D'
        submission.time = time
        submission.memory = memory
        submission.points = sub_points
        submission.result = status_codes[status]
        submission.save()

        json_log.info(self._make_json_log(
            packet, action='grading-end', time=time, memory=memory,
            points=sub_points, total=problem.points, result=submission.result,
            case_points=points, case_total=total, user=submission.user_id,
            problem=problem.code, finish=True
        ))

        submission.user._updating_stats_only = True
        submission.user.calculate_points()
        problem._updating_stats_only = True
        problem.update_stats()

        submission.recalculate_contest_submission()

        finished_submission(submission)

        event.post('sub_%s' % submission.id_secret, {
            'type': 'grading-end',
            'time': time,
            'memory': memory,
            'points': float(points),
            'total': float(problem.points),
            'result': submission.result
        })
        if hasattr(submission, 'contest'):
            participation = submission.contest.participation
            event.post('contest_%d' % participation.contest_id, {'type': 'update'})
        self._post_update_submission(submission.id, 'grading-end', done=True)

    def on_compile_error(self, packet):
        super(DjangoJudgeHandler, self).on_compile_error(packet)

        if Submission.objects.filter(id=packet['submission-id']).update(status='CE', result='CE', error=packet['log']):
            event.post('sub_%s' % Submission.get_id_secret(packet['submission-id']), {
                'type': 'compile-error',
                'log': packet['log']
            })
            self._post_update_submission(packet['submission-id'], 'compile-error', done=True)
            json_log.info(self._make_json_log(packet, action='compile-error', log=packet['log'],
                                              finish=True, result='CE'))
        else:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            json_log.error(self._make_json_log(packet, action='compile-error', info='unknown submission',
                                               log=packet['log'], finish=True, result='CE'))

    def on_compile_message(self, packet):
        super(DjangoJudgeHandler, self).on_compile_message(packet)

        if Submission.objects.filter(id=packet['submission-id']).update(error=packet['log']):
            event.post('sub_%s' % Submission.get_id_secret(packet['submission-id']), {'type': 'compile-message'})
            json_log.info(self._make_json_log(packet, action='compile-message', log=packet['log']))
        else:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            json_log.error(self._make_json_log(packet, action='compile-message', info='unknown submission',
                                               log=packet['log']))

    def on_internal_error(self, packet):
        super(DjangoJudgeHandler, self).on_internal_error(packet)

        id = packet['submission-id']
        if Submission.objects.filter(id=id).update(status='IE', result='IE', error=packet['message']):
            event.post('sub_%s' % Submission.get_id_secret(id), {'type': 'internal-error'})
            self._post_update_submission(id, 'internal-error', done=True)
            json_log.info(self._make_json_log(packet, action='internal-error', message=packet['message'],
                                              finish=True, result='IE'))
        else:
            logger.warning('Unknown submission: %d', id)
            json_log.error(self._make_json_log(packet, action='internal-error', info='unknown submission',
                                               message=packet['message'], finish=True, result='IE'))

    def on_submission_terminated(self, packet):
        super(DjangoJudgeHandler, self).on_submission_terminated(packet)

        if Submission.objects.filter(id=packet['submission-id']).update(status='AB', result='AB'):
            event.post('sub_%s' % Submission.get_id_secret(packet['submission-id']), {'type': 'aborted-submission'})
            self._post_update_submission(packet['submission-id'], 'terminated', done=True)
            json_log.info(self._make_json_log(packet, action='aborted', finish=True, result='AB'))
        else:
            logger.warning('Unknown submission: %d', packet['submission-id'])
            json_log.error(self._make_json_log(packet, action='aborted', info='unknown submission',
                                               finish=True, result='AB'))

    def on_batch_begin(self, packet):
        super(DjangoJudgeHandler, self).on_batch_begin(packet)
        json_log.info(self._make_json_log(packet, action='batch-begin', batch=self.batch_id))

    def on_batch_end(self, packet):
        super(DjangoJudgeHandler, self).on_batch_end(packet)
        json_log.info(self._make_json_log(packet, action='batch-end', batch=self.batch_id))

    def on_test_case(self, packet, max_feedback=SubmissionTestCase._meta.get_field('feedback').max_length):
        super(DjangoJudgeHandler, self).on_test_case(packet)
        id = packet['submission-id']

        if not Submission.objects.filter(id=id).update(current_testcase=packet['position'] + 1):
            logger.warning('Unknown submission: %d', id)
            json_log.error(self._make_json_log(packet, action='test-case', info='unknown submission'))
            return

        test_case = SubmissionTestCase(submission_id=id, case=packet['position'])
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
        test_case.feedback = (packet.get('feedback', None) or '')[:max_feedback]
        test_case.output = packet['output']
        test_case.save()

        json_log.info(self._make_json_log(
            packet, action='test-case', case=test_case.case, batch=test_case.batch,
            time=test_case.time, memory=test_case.memory, feedback=test_case.feedback,
            output=test_case.output, points=test_case.points, total=test_case.total,
            status=test_case.status
        ))

        do_post = True

        if id in self.update_counter:
            cnt, reset = self.update_counter[id]
            cnt += 1
            if TIMER() - reset > UPDATE_RATE_TIME:
                del self.update_counter[id]
            else:
                self.update_counter[id] = (cnt, reset)
                if cnt > UPDATE_RATE_LIMIT:
                    do_post = False
        if id not in self.update_counter:
            self.update_counter[id] = (1, TIMER())

        if do_post:
            event.post('sub_%s' % Submission.get_id_secret(id), {
                'type': 'test-case',
                'id': packet['position'],
                'status': test_case.status,
                'time': '%.3f' % round(float(packet['time']), 3),
                'memory': packet['memory'],
                'points': float(test_case.points),
                'total': float(test_case.total),
                'output': packet['output']
            })
            self._post_update_submission(id, state='test-case')

    def on_supported_problems(self, packet):
        super(DjangoJudgeHandler, self).on_supported_problems(packet)
        self.judge.problems.set(Problem.objects.filter(code__in=self.problems.keys()))
        json_log.info(self._make_json_log(action='update-problems', count=len(self.problems)))

    def _make_json_log(self, packet=None, sub=None, **kwargs):
        data = {
            'judge': self.name,
            'address': self.judge_address,
        }
        if sub is None and packet is not None:
            sub = packet.get('submission-id')
        if sub is not None:
            data['submission'] = sub
        data.update(kwargs)
        return json.dumps(data)
