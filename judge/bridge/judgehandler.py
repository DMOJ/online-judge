from __future__ import division

import logging
import json
import threading
import time

from collections import deque
from event_socket_server import ZlibPacketHandler

logger = logging.getLogger('judge.bridge')


class JudgeHandler(ZlibPacketHandler):
    def __init__(self, server, socket):
        super(JudgeHandler, self).__init__(server, socket)

        self.handlers = {
            'grading-begin': self.on_grading_begin,
            'grading-end': self.on_grading_end,
            'compile-error': self.on_compile_error,
            'batch-begin': self.on_batch_begin,
            'batch-end': self.on_batch_end,
            'test-case-status': self.on_test_case,
            'problem-not-exist': self.on_bad_problem,
            'submission-terminated': self.on_submission_terminated,
            'submission-acknowledged': self.on_submission_acknowledged,
            'ping-response': self.on_ping_response,
            'supported-problems': self.on_supported_problems,
            'handshake': self.on_handshake,
        }
        self._to_kill = True
        self._working = False
        self._received = threading.Event()
        self._no_response_job = None
        self._problems = []
        self.executors = []
        self.problems = {}
        self.latency = None
        self.time_delta = None
        self.load = 1e100
        self.name = None
        self.batch_id = None
        self.client_address = socket.getpeername()
        self._ping_average = deque(maxlen=6)  # 1 minute average, just like load
        self._time_delta = deque(maxlen=6)

        self.server.schedule(5, self._kill_if_no_auth)
        logger.info('Judge connected from: %s', self.client_address)

    def _kill_if_no_auth(self):
        if self._to_kill:
            logger.info('Judge not authenticated: %s', self.client_address)
            self.close()

    def on_close(self):
        self._to_kill = False
        self.server.judges.remove(self)
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

    def _format_send(self, data):
        return super(JudgeHandler, self)._format_send(json.dumps(data, separators=(',', ':')))

    def on_handshake(self, packet):
        if 'id' not in packet or 'key' not in packet or not self._authenticate(packet['id'], packet['key']):
            self.close()

        self._to_kill = False
        self._problems = packet['problems']
        self.problems = dict(self._problems)
        self.executors = packet['executors']
        self.name = packet['id']

        self.send({'name': 'handshake-success'})
        logger.info('Judge authenticated: %s', self.client_address)
        self.server.judges.register(self)
        self._connected()

    def can_judge(self, problem, executor):
        return problem in self.problems and executor in self.executors

    @property
    def working(self):
        return bool(self._working)

    def problem_data(self, problem):
        return 2, 16384, False

    def submit(self, id, problem, language, source):
        time, memory, short = self.problem_data(problem)
        self.send({
            'name': 'submission-request',
            'submission-id': id,
            'problem-id': problem,
            'language': language,
            'source': source,
            'time-limit': time,
            'memory-limit': memory,
            'short-circuit': short,
        })
        self._working = id
        self._no_response_job = self.server.schedule(20, self._kill_if_no_response)
        self._received.clear()

    def _kill_if_no_response(self):
        logger.error('Judge seems dead: %s: %s', self.name, self._working)
        self.close()

    def on_submission_acknowledged(self, packet):
        if not packet.get('submission-id', None) == self._working:
            logger.error('Wrong acknowledgement: %s: %s, expected: %s', self.name, packet.get('submission-id', None),
                         self._working)
            self.close()
            return
        logger.info('Submission acknowledged: %d', self._working)
        if self._no_response_job:
            self.server.unschedule(self._no_response_job)
            self._received.set()
            self._no_response_job = None

    def abort(self):
        self.send({'name': 'terminate-submission'})

    def get_current_submission(self):
        return self._working or None

    def ping(self):
        self.send({'name': 'ping', 'when': time.time()})

    def packet(self, data):
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
        except:
            logger.exception('Error in packet handling (Judge-side)')
            # You can't crash here because you aren't so sure about the judges
            # not being malicious or simply malforms. THIS IS A SERVER!

    def _submission_is_batch(self, id):
        pass

    def on_supported_problems(self, packet):
        logger.info('Updated problem list')
        self._problems = packet['problems']
        self.problems = dict(self._problems)
        if not self.working:
            self.server.judges.update_problems(self)

    def on_grading_begin(self, packet):
        logger.info('Grading has begun on: %s', packet['submission-id'])
        self.batch_id = None

    def on_grading_end(self, packet):
        logger.info('Grading has ended on: %s', packet['submission-id'])
        self._free_self(packet)
        self.batch_id = None

    def on_compile_error(self, packet):
        logger.info('Submission failed to compile: %s', packet['submission-id'])
        self._free_self(packet)

    def on_bad_problem(self, packet):
        logger.error('Submission referenced invalid problem "%s": %s', packet['problem'], packet['submission-id'])
        self._free_self(packet)

    def on_submission_terminated(self, packet):
        logger.info('Submission aborted: %s', packet['submission-id'])
        self._free_self(packet)

    def on_batch_begin(self, packet):
        logger.info('Batch began on: %s', packet['submission-id'])
        if self.batch_id is None:
            self.batch_id = 0
            self._submission_is_batch(packet['submission-id'])
        self.batch_id += 1

    def on_batch_end(self, packet):
        logger.info('Batch ended on: %s', packet['submission-id'])

    def on_test_case(self, packet):
        logger.info('Test case completed on: %s', packet['submission-id'])

    def on_malformed(self, packet):
        logger.error('Malformed packet: %s', packet)

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
        self.server.judges.on_judge_free(self, packet['submission-id'])
