import hmac
import json
import logging
import threading
import time
from collections import deque, namedtuple
from operator import itemgetter

from django import db
from django.conf import settings
from django.utils import timezone

from judge import event_poster as event
from judge.bridge.base_handler import ZlibPacketHandler, proxy_list
from judge.caching import finished_submission
from judge.models import Judge, Language, LanguageLimit, Problem, RuntimeVersion, Submission, SubmissionTestCase

logger = logging.getLogger('judge.bridge')
json_log = logging.getLogger('judge.json.bridge')

UPDATE_RATE_LIMIT = 5
UPDATE_RATE_TIME = 0.5
SubmissionData = namedtuple('SubmissionData', 'time memory short_circuit pretests_only contest_no attempt_no user_id')


def _ensure_connection():
    try:
        db.connection.cursor().execute('SELECT 1').fetchall()
    except Exception:
        db.connection.close()


class JudgeHandler(ZlibPacketHandler):
    proxies = proxy_list(settings.BRIDGED_JUDGE_PROXIES or [])

    def __init__(self, request, client_address, server, judges):
        super().__init__(request, client_address, server)

        self.judges = judges
        self.handlers = {
            'grading-begin': self.on_grading_begin,
            'grading-end': self.on_grading_end,
            'compile-error': self.on_compile_error,
            'compile-message': self.on_compile_message,
            'batch-begin': self.on_batch_begin,
            'batch-end': self.on_batch_end,
            'test-case-status': self.on_test_case,
            'internal-error': self.on_internal_error,
            'submission-terminated': self.on_submission_terminated,
            'submission-acknowledged': self.on_submission_acknowledged,
            'ping-response': self.on_ping_response,
            'supported-problems': self.on_supported_problems,
            'handshake': self.on_handshake,
        }
        self._working = False
        self._no_response_job = None
        self._problems = []
        self.executors = {}
        self.problems = {}
        self.latency = None
        self.time_delta = None
        self.load = 1e100
        self.name = None
        self.batch_id = None
        self.in_batch = False
        self._stop_ping = threading.Event()
        self._ping_average = deque(maxlen=6)  # 1 minute average, just like load
        self._time_delta = deque(maxlen=6)

        # each value is (updates, last reset)
        self.update_counter = {}
        self.judge = None
        self.judge_address = None

        self._submission_cache_id = None
        self._submission_cache = {}

    def on_connect(self):
        self.timeout = 15
        logger.info('Judge connected from: %s', self.client_address)
        json_log.info(self._make_json_log(action='connect'))

    def on_disconnect(self):
        self._stop_ping.set()
        if self._working:
            logger.error('Judge %s disconnected while handling submission %s', self.name, self._working)
        self.judges.remove(self)
        if self.name is not None:
            self._disconnected()
        logger.info('Judge disconnected from: %s with name %s', self.client_address, self.name)

        json_log.info(self._make_json_log(action='disconnect', info='judge disconnected'))
        if self._working:
            Submission.objects.filter(id=self._working).update(status='IE', result='IE', error='')
            json_log.error(self._make_json_log(sub=self._working, action='close', info='IE due to shutdown on grading'))

    def _authenticate(self, id, key):
        try:
            judge = Judge.objects.get(name=id, is_blocked=False)
        except Judge.DoesNotExist:
            result = False
        else:
            result = hmac.compare_digest(judge.auth_key, key)

        if not result:
            json_log.warning(self._make_json_log(action='auth', judge=id, info='judge failed authentication'))
        return result

    def _connected(self):
        judge = self.judge = Judge.objects.get(name=self.name)
        judge.start_time = timezone.now()
        judge.online = True
        judge.problems.set(Problem.objects.filter(code__in=list(self.problems.keys())))
        judge.runtimes.set(Language.objects.filter(key__in=list(self.executors.keys())))

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
                                          executors=list(self.executors.keys())))

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

    def send(self, data):
        super().send(json.dumps(data, separators=(',', ':')))

    def on_handshake(self, packet):
        if 'id' not in packet or 'key' not in packet:
            logger.warning('Malformed handshake: %s', self.client_address)
            self.close()
            return

        if not self._authenticate(packet['id'], packet['key']):
            logger.warning('Authentication failure: %s', self.client_address)
            self.close()
            return

        self.timeout = 60
        self._problems = packet['problems']
        self.problems = dict(self._problems)
        self.executors = packet['executors']
        self.name = packet['id']

        self.send({'name': 'handshake-success'})
        logger.info('Judge authenticated: %s (%s)', self.client_address, packet['id'])
        self.judges.register(self)
        threading.Thread(target=self._ping_thread).start()
        self._connected()

    def can_judge(self, problem, executor, judge_id=None):
        return problem in self.problems and executor in self.executors and (not judge_id or self.name == judge_id)

    @property
    def working(self):
        return bool(self._working)

    def get_related_submission_data(self, submission):
        _ensure_connection()

        try:
            pid, time, memory, short_circuit, lid, is_pretested, sub_date, uid, part_virtual, part_id = (
                Submission.objects.filter(id=submission)
                          .values_list('problem__id', 'problem__time_limit', 'problem__memory_limit',
                                       'problem__short_circuit', 'language__id', 'is_pretested', 'date', 'user__id',
                                       'contest__participation__virtual', 'contest__participation__id')).get()
        except Submission.DoesNotExist:
            logger.error('Submission vanished: %s', submission)
            json_log.error(self._make_json_log(
                sub=self._working, action='request',
                info='submission vanished when fetching info',
            ))
            return

        attempt_no = Submission.objects.filter(problem__id=pid, contest__participation__id=part_id, user__id=uid,
                                               date__lt=sub_date).exclude(status__in=('CE', 'IE')).count() + 1

        try:
            time, memory = (LanguageLimit.objects.filter(problem__id=pid, language__id=lid)
                            .values_list('time_limit', 'memory_limit').get())
        except LanguageLimit.DoesNotExist:
            pass

        return SubmissionData(
            time=time,
            memory=memory,
            short_circuit=short_circuit,
            pretests_only=is_pretested,
            contest_no=part_virtual,
            attempt_no=attempt_no,
            user_id=uid,
        )

    def disconnect(self, force=False):
        if force:
            # Yank the power out.
            self.close()
        else:
            self.send({'name': 'disconnect'})

    def submit(self, id, problem, language, source):
        data = self.get_related_submission_data(id)
        self._working = id
        self._no_response_job = threading.Timer(20, self._kill_if_no_response)
        self.send({
            'name': 'submission-request',
            'submission-id': id,
            'problem-id': problem,
            'language': language,
            'source': source,
            'time-limit': data.time,
            'memory-limit': data.memory,
            'short-circuit': data.short_circuit,
            'meta': {
                'pretests-only': data.pretests_only,
                'in-contest': data.contest_no,
                'attempt-no': data.attempt_no,
                'user': data.user_id,
            },
        })

    def _kill_if_no_response(self):
        logger.error('Judge failed to acknowledge submission: %s: %s', self.name, self._working)
        self.close()

    def on_timeout(self):
        if self.name:
            logger.warning('Judge seems dead: %s: %s', self.name, self._working)

    def malformed_packet(self, exception):
        logger.exception('Judge sent malformed packet: %s', self.name)
        super(JudgeHandler, self).malformed_packet(exception)

    def on_submission_processing(self, packet):
        _ensure_connection()

        id = packet['submission-id']
        if Submission.objects.filter(id=id).update(status='P', judged_on=self.judge):
            event.post('sub_%s' % Submission.get_id_secret(id), {'type': 'processing'})
            self._post_update_submission(id, 'processing')
            json_log.info(self._make_json_log(packet, action='processing'))
        else:
            logger.warning('Unknown submission: %s', id)
            json_log.error(self._make_json_log(packet, action='processing', info='unknown submission'))

    def on_submission_wrong_acknowledge(self, packet, expected, got):
        json_log.error(self._make_json_log(packet, action='processing', info='wrong-acknowledge', expected=expected))
        Submission.objects.filter(id=expected).update(status='IE', result='IE', error=None)
        Submission.objects.filter(id=got, status='QU').update(status='IE', result='IE', error=None)

    def on_submission_acknowledged(self, packet):
        if not packet.get('submission-id', None) == self._working:
            logger.error('Wrong acknowledgement: %s: %s, expected: %s', self.name, packet.get('submission-id', None),
                         self._working)
            self.on_submission_wrong_acknowledge(packet, self._working, packet.get('submission-id', None))
            self.close()
        logger.info('Submission acknowledged: %d', self._working)
        if self._no_response_job:
            self._no_response_job.cancel()
            self._no_response_job = None
        self.on_submission_processing(packet)

    def abort(self):
        self.send({'name': 'terminate-submission'})

    def get_current_submission(self):
        return self._working or None

    def ping(self):
        self.send({'name': 'ping', 'when': time.time()})

    def on_packet(self, data):
        try:
            try:
                data = json.loads(data)
                if 'name' not in data:
                    raise ValueError
            except ValueError:
                self.on_malformed(data)
            else:
                handler = self.handlers.get(data['name'], self.on_malformed)
                handler(data)
        except Exception:
            logger.exception('Error in packet handling (Judge-side): %s', self.name)
            self._packet_exception()
            # You can't crash here because you aren't so sure about the judges
            # not being malicious or simply malforms. THIS IS A SERVER!

    def _packet_exception(self):
        json_log.exception(self._make_json_log(sub=self._working, info='packet processing exception'))

    def _submission_is_batch(self, id):
        if not Submission.objects.filter(id=id).update(batch=True):
            logger.warning('Unknown submission: %s', id)

    def on_supported_problems(self, packet):
        logger.info('%s: Updated problem list', self.name)
        self._problems = packet['problems']
        self.problems = dict(self._problems)
        if not self.working:
            self.judges.update_problems(self)

        self.judge.problems.set(Problem.objects.filter(code__in=list(self.problems.keys())))
        json_log.info(self._make_json_log(action='update-problems', count=len(self.problems)))

    def on_grading_begin(self, packet):
        logger.info('%s: Grading has begun on: %s', self.name, packet['submission-id'])
        self.batch_id = None

        if Submission.objects.filter(id=packet['submission-id']).update(
                status='G', is_pretested=packet['pretested'], current_testcase=1,
                batch=False, judged_date=timezone.now()):
            SubmissionTestCase.objects.filter(submission_id=packet['submission-id']).delete()
            event.post('sub_%s' % Submission.get_id_secret(packet['submission-id']), {'type': 'grading-begin'})
            self._post_update_submission(packet['submission-id'], 'grading-begin')
            json_log.info(self._make_json_log(packet, action='grading-begin'))
        else:
            logger.warning('Unknown submission: %s', packet['submission-id'])
            json_log.error(self._make_json_log(packet, action='grading-begin', info='unknown submission'))

    def on_grading_end(self, packet):
        logger.info('%s: Grading has ended on: %s', self.name, packet['submission-id'])
        self._free_self(packet)
        self.batch_id = None

        try:
            submission = Submission.objects.get(id=packet['submission-id'])
        except Submission.DoesNotExist:
            logger.warning('Unknown submission: %s', packet['submission-id'])
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
            problem=problem.code, finish=True,
        ))

        if problem.is_public and not problem.is_organization_private:
            submission.user._updating_stats_only = True
            submission.user.calculate_points()

        problem._updating_stats_only = True
        problem.update_stats()
        submission.update_contest()

        finished_submission(submission)

        event.post('sub_%s' % submission.id_secret, {
            'type': 'grading-end',
            'time': time,
            'memory': memory,
            'points': float(points),
            'total': float(problem.points),
            'result': submission.result,
        })
        if hasattr(submission, 'contest'):
            participation = submission.contest.participation
            event.post('contest_%d' % participation.contest_id, {'type': 'update'})
        self._post_update_submission(submission.id, 'grading-end', done=True)

    def on_compile_error(self, packet):
        logger.info('%s: Submission failed to compile: %s', self.name, packet['submission-id'])
        self._free_self(packet)

        if Submission.objects.filter(id=packet['submission-id']).update(status='CE', result='CE', error=packet['log']):
            event.post('sub_%s' % Submission.get_id_secret(packet['submission-id']), {
                'type': 'compile-error',
                'log': packet['log'],
            })
            self._post_update_submission(packet['submission-id'], 'compile-error', done=True)
            json_log.info(self._make_json_log(packet, action='compile-error', log=packet['log'],
                                              finish=True, result='CE'))
        else:
            logger.warning('Unknown submission: %s', packet['submission-id'])
            json_log.error(self._make_json_log(packet, action='compile-error', info='unknown submission',
                                               log=packet['log'], finish=True, result='CE'))

    def on_compile_message(self, packet):
        logger.info('%s: Submission generated compiler messages: %s', self.name, packet['submission-id'])

        if Submission.objects.filter(id=packet['submission-id']).update(error=packet['log']):
            event.post('sub_%s' % Submission.get_id_secret(packet['submission-id']), {'type': 'compile-message'})
            json_log.info(self._make_json_log(packet, action='compile-message', log=packet['log']))
        else:
            logger.warning('Unknown submission: %s', packet['submission-id'])
            json_log.error(self._make_json_log(packet, action='compile-message', info='unknown submission',
                                               log=packet['log']))

    def on_internal_error(self, packet):
        try:
            raise ValueError('\n\n' + packet['message'])
        except ValueError:
            logger.exception('Judge %s failed while handling submission %s', self.name, packet['submission-id'])
        self._free_self(packet)

        id = packet['submission-id']
        if Submission.objects.filter(id=id).update(status='IE', result='IE', error=packet['message']):
            event.post('sub_%s' % Submission.get_id_secret(id), {'type': 'internal-error'})
            self._post_update_submission(id, 'internal-error', done=True)
            json_log.info(self._make_json_log(packet, action='internal-error', message=packet['message'],
                                              finish=True, result='IE'))
        else:
            logger.warning('Unknown submission: %s', id)
            json_log.error(self._make_json_log(packet, action='internal-error', info='unknown submission',
                                               message=packet['message'], finish=True, result='IE'))

    def on_submission_terminated(self, packet):
        logger.info('%s: Submission aborted: %s', self.name, packet['submission-id'])
        self._free_self(packet)

        if Submission.objects.filter(id=packet['submission-id']).update(status='AB', result='AB'):
            event.post('sub_%s' % Submission.get_id_secret(packet['submission-id']), {'type': 'aborted-submission'})
            self._post_update_submission(packet['submission-id'], 'terminated', done=True)
            json_log.info(self._make_json_log(packet, action='aborted', finish=True, result='AB'))
        else:
            logger.warning('Unknown submission: %s', packet['submission-id'])
            json_log.error(self._make_json_log(packet, action='aborted', info='unknown submission',
                                               finish=True, result='AB'))

    def on_batch_begin(self, packet):
        logger.info('%s: Batch began on: %s', self.name, packet['submission-id'])
        self.in_batch = True
        if self.batch_id is None:
            self.batch_id = 0
            self._submission_is_batch(packet['submission-id'])
        self.batch_id += 1

        json_log.info(self._make_json_log(packet, action='batch-begin', batch=self.batch_id))

    def on_batch_end(self, packet):
        self.in_batch = False
        logger.info('%s: Batch ended on: %s', self.name, packet['submission-id'])
        json_log.info(self._make_json_log(packet, action='batch-end', batch=self.batch_id))

    def on_test_case(self, packet, max_feedback=SubmissionTestCase._meta.get_field('feedback').max_length):
        logger.info('%s: %d test case(s) completed on: %s', self.name, len(packet['cases']), packet['submission-id'])

        id = packet['submission-id']
        updates = packet['cases']
        max_position = max(map(itemgetter('position'), updates))

        if not Submission.objects.filter(id=id).update(current_testcase=max_position + 1):
            logger.warning('Unknown submission: %s', id)
            json_log.error(self._make_json_log(packet, action='test-case', info='unknown submission'))
            return

        bulk_test_case_updates = []
        for result in updates:
            test_case = SubmissionTestCase(submission_id=id, case=result['position'])
            status = result['status']
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
            test_case.time = result['time']
            test_case.memory = result['memory']
            test_case.points = result['points']
            test_case.total = result['total-points']
            test_case.batch = self.batch_id if self.in_batch else None
            test_case.feedback = (result.get('feedback') or '')[:max_feedback]
            test_case.extended_feedback = result.get('extended-feedback') or ''
            test_case.output = result['output']
            bulk_test_case_updates.append(test_case)

            json_log.info(self._make_json_log(
                packet, action='test-case', case=test_case.case, batch=test_case.batch,
                time=test_case.time, memory=test_case.memory, feedback=test_case.feedback,
                extended_feedback=test_case.extended_feedback, output=test_case.output,
                points=test_case.points, total=test_case.total, status=test_case.status,
            ))

        do_post = True

        if id in self.update_counter:
            cnt, reset = self.update_counter[id]
            cnt += 1
            if time.monotonic() - reset > UPDATE_RATE_TIME:
                del self.update_counter[id]
            else:
                self.update_counter[id] = (cnt, reset)
                if cnt > UPDATE_RATE_LIMIT:
                    do_post = False
        if id not in self.update_counter:
            self.update_counter[id] = (1, time.monotonic())

        if do_post:
            event.post('sub_%s' % Submission.get_id_secret(id), {
                'type': 'test-case',
                'id': max_position,
            })
            self._post_update_submission(id, state='test-case')

        SubmissionTestCase.objects.bulk_create(bulk_test_case_updates)

    def on_malformed(self, packet):
        logger.error('%s: Malformed packet: %s', self.name, packet)
        json_log.exception(self._make_json_log(sub=self._working, info='malformed json packet'))

    def on_ping_response(self, packet):
        end = time.time()
        self._ping_average.append(end - packet['when'])
        self._time_delta.append((end + packet['when']) / 2 - packet['time'])
        self.latency = sum(self._ping_average) / len(self._ping_average)
        self.time_delta = sum(self._time_delta) / len(self._time_delta)
        self.load = packet['load']
        self._update_ping()

    def _free_self(self, packet):
        self.judges.on_judge_free(self, packet['submission-id'])

    def _ping_thread(self):
        try:
            while True:
                self.ping()
                if self._stop_ping.wait(10):
                    break
        except Exception:
            logger.exception('Ping error in %s', self.name)
            self.close()
            raise

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

    def _post_update_submission(self, id, state, done=False):
        if self._submission_cache_id == id:
            data = self._submission_cache
        else:
            self._submission_cache = data = Submission.objects.filter(id=id).values(
                'problem__is_public', 'contest_object__key',
                'user_id', 'problem_id', 'status', 'language__key',
            ).get()
            self._submission_cache_id = id

        if data['problem__is_public']:
            event.post('submissions', {
                'type': 'done-submission' if done else 'update-submission',
                'state': state, 'id': id,
                'contest': data['contest_object__key'],
                'user': data['user_id'], 'problem': data['problem_id'],
                'status': data['status'], 'language': data['language__key'],
            })
