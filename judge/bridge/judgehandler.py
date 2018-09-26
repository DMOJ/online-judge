from __future__ import division

import json
import logging
import time
from collections import deque

from event_socket_server import ZlibPacketHandler, ProxyProtocolMixin

logger = logging.getLogger('judge.bridge')


class JudgeHandler(ProxyProtocolMixin, ZlibPacketHandler):
    def __init__(self, server, socket):
        super(JudgeHandler, self).__init__(server, socket)

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
        self._to_kill = True
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
        self._ping_average = deque(maxlen=6)  # 1 minute average, just like load
        self._time_delta = deque(maxlen=6)

        self.server.schedule(15, self._kill_if_no_auth)
        logger.info('Judge connected from: %s', self.client_address)

    def _kill_if_no_auth(self):
        if self._to_kill:
            logger.info('Judge not authenticated: %s', self.client_address)
            self.close()

    def on_close(self):
        self._to_kill = False
        if self._no_response_job:
            self.server.unschedule(self._no_response_job)
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
        if 'id' not in packet or 'key' not in packet:
            logger.warning('Malformed handshake: %s', self.client_address)
            self.close()
            return

        if not self._authenticate(packet['id'], packet['key']):
            logger.warning('Authentication failure: %s', self.client_address)
            self.close()
            return

        self._to_kill = False
        self._problems = packet['problems']
        self.problems = dict(self._problems)
        self.executors = packet['executors']
        self.name = packet['id']

        self.send({'name': 'handshake-success'})
        logger.info('Judge authenticated: %s (%s)', self.client_address, packet['id'])
        self.server.judges.register(self)
        self._connected()

    def can_judge(self, problem, executor):
        return problem in self.problems and executor in self.executors

    @property
    def working(self):
        return bool(self._working)

    def get_related_submission_data(self, submission):
        return 2, 16384, False, False

    def disconnect(self, force=False):
        if force:
            # Yank the power out.
            self.close()
        else:
            self.send({'name': 'disconnect'})

    def submit(self, id, problem, language, source):
        time, memory, short, pretests_only = self.get_related_submission_data(id)
        self._working = id
        self._no_response_job = self.server.schedule(20, self._kill_if_no_response)
        self.send({
            'name': 'submission-request',
            'submission-id': id,
            'problem-id': problem,
            'language': language,
            'source': source,
            'time-limit': time,
            'memory-limit': memory,
            'short-circuit': short,
            'pretests-only': pretests_only,
        })

    def _kill_if_no_response(self):
        logger.error('Judge seems dead: %s: %s', self.name, self._working)
        self.close()

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
            self.server.unschedule(self._no_response_job)
            self._no_response_job = None
        self.on_submission_processing(packet)

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
            self.server.judges.update_problems(self)

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
        logger.info('%s: Test case completed on: %s', self.name, packet['submission-id'])

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
        self.server.judges.on_judge_free(self, packet['submission-id'])
