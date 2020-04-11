import json
import logging
import threading
import time
from collections import deque, namedtuple

from judge.bridge.base_handler import ZlibPacketHandler

logger = logging.getLogger('judge.bridge')

SubmissionData = namedtuple('SubmissionData', 'time memory short_circuit pretests_only contest_no attempt_no user_id')


class JudgeHandler(ZlibPacketHandler):
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
        self.executors = []
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

    def on_connect(self):
        self.timeout = 15
        logger.info('Judge connected from: %s', self.client_address)

    def on_disconnect(self):
        self._stop_ping.set()
        if self._working:
            logger.error('Judge %s disconnected while handling submission %s', self.name, self._working)
        self.judges.remove(self)
        if self.name is not None:
            self._disconnected()
        logger.info('Judge disconnected from: %s', self.client_address)

    def _authenticate(self, id, key):
        return False

    def _connected(self):
        pass

    def _disconnected(self):
        pass

    def _update_ping(self):
        pass

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

    def can_judge(self, problem, executor):
        return problem in self.problems and executor in self.executors

    @property
    def working(self):
        return bool(self._working)

    def get_related_submission_data(self, submission):
        return SubmissionData(
            time=2,
            memory=16384,
            short_circuit=False,
            pretests_only=False,
            contest_no=None,
            attempt_no=1,
            user_id=None,
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
        logger.error('Judge seems dead: %s: %s', self.name, self._working)

    def malformed_packet(self, exception):
        logger.exception('Judge sent malformed packet: %s', self.name)
        super(JudgeHandler, self).malformed_packet(exception)

    def on_submission_processing(self, packet):
        pass

    def on_submission_wrong_acknowledge(self, packet, expected, got):
        pass

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
        pass

    def _submission_is_batch(self, id):
        pass

    def on_supported_problems(self, packet):
        logger.info('%s: Updated problem list', self.name)
        self._problems = packet['problems']
        self.problems = dict(self._problems)
        if not self.working:
            self.judges.update_problems(self)

    def on_grading_begin(self, packet):
        logger.info('%s: Grading has begun on: %s', self.name, packet['submission-id'])
        self.batch_id = None

    def on_grading_end(self, packet):
        logger.info('%s: Grading has ended on: %s', self.name, packet['submission-id'])
        self._free_self(packet)
        self.batch_id = None

    def on_compile_error(self, packet):
        logger.info('%s: Submission failed to compile: %s', self.name, packet['submission-id'])
        self._free_self(packet)

    def on_compile_message(self, packet):
        logger.info('%s: Submission generated compiler messages: %s', self.name, packet['submission-id'])

    def on_internal_error(self, packet):
        try:
            raise ValueError('\n\n' + packet['message'])
        except ValueError:
            logger.exception('Judge %s failed while handling submission %s', self.name, packet['submission-id'])
        self._free_self(packet)

    def on_submission_terminated(self, packet):
        logger.info('%s: Submission aborted: %s', self.name, packet['submission-id'])
        self._free_self(packet)

    def on_batch_begin(self, packet):
        logger.info('%s: Batch began on: %s', self.name, packet['submission-id'])
        self.in_batch = True
        if self.batch_id is None:
            self.batch_id = 0
            self._submission_is_batch(packet['submission-id'])
        self.batch_id += 1

    def on_batch_end(self, packet):
        self.in_batch = False
        logger.info('%s: Batch ended on: %s', self.name, packet['submission-id'])

    def on_test_case(self, packet):
        logger.info('%s: %d test case(s) completed on: %s', self.name, len(packet['cases']), packet['submission-id'])

    def on_malformed(self, packet):
        logger.error('%s: Malformed packet: %s', self.name, packet)

    def on_ping_response(self, packet):
        end = time.time()
        self._ping_average.append(end - packet['when'])
        self._time_delta.append((end + packet['when']) / 2 - packet['time'])
        self.latency = sum(self._ping_average) / len(self._ping_average)
        self.time_delta = sum(self._time_delta) / len(self._time_delta)
        self.load = packet['load']
        self._update_ping()

    def _free_self(self, packet):
        self._working = False
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
