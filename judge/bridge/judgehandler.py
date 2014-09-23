import logging
import socket
import SocketServer
import struct
import json
import threading
import time

size_pack = struct.Struct('!I')
logger = logging.getLogger('judge.bridge')


class JudgeHandler(SocketServer.StreamRequestHandler):
    def setup(self):
        SocketServer.StreamRequestHandler.setup(self)

        self.handlers = {
            'grading-begin': self.on_grading_begin,
            'grading-end': self.on_grading_end,
            'compile-error': self.on_compile_error,
            'test-case-status': self.on_test_case,
            'current-submission-id': self.on_current_submission,
            'problem-not-exist': self.on_bad_problem,
            'submission-terminated': self.on_submission_terminated,
            'supported-problems': self.on_supported_problems,
            'ping-response': self.on_ping_response
        }
        self._current_submission = None
        self._current_submission_event = threading.Event()
        self._working = False
        self._problems = []
        self.problems = {}
        self.latency = None
        self.load = 1e100

        logger.info('Judge connected from: %s', self.client_address)
        self.server.judges.append(self)

    def finish(self):
        SocketServer.StreamRequestHandler.finish(self)
        logger.info('Judge disconnected from: %s', self.client_address)
        self.server.judges.remove(self)

    def handle(self):
        self.ping()
        while True:
            try:
                buf = self.rfile.read(size_pack.size)
                if not buf:
                    break
                size = size_pack.unpack(buf)[0]
                data = self.rfile.read(size)
                if not data:
                    break
                data = data.decode('zlib')
                payload = json.loads(data)
                self._packet(payload)
            except socket.error:
                self.rfile.close()
                self.wfile.close()
                break

    @property
    def working(self):
        return bool(self._working)

    def problem_data(self, problem):
        return 2, 16384, False, 'standard', {}

    def submit(self, id, problem, language, source):
        time, memory, short, grader, param = self.problem_data(problem)
        packet = {
            'name': 'submission-request',
            'submission-id': id,
            'problem-id': problem,
            'language': language,
            'source': source,
            'time-limit': time,
            'memory-limit': memory,
            'short-circuit': short,
            'grader-id': grader,
            'grader-args': param

        }
        self._send(packet)
        self._working = id

    def abort(self):
        self._send({'name': 'terminate-submission'})

    def get_current_submission(self):
        self._send({'name': 'get-current-submission'})
        self._current_submission_event.wait()
        self._current_submission_event.clear()
        return self._current_submission

    def ping(self):
        self._send({'name': 'ping', 'when': time.time()})

    def _send(self, data):
        data = json.dumps(data, separators=(',', ':'))
        compress = data.encode('zlib')
        self.wfile.write(size_pack.pack(len(compress)))
        self.wfile.write(compress)

    def _packet(self, data):
        try:
            if 'name' not in data:
                self.on_malformed(data)
            handler = self.handlers.get(data['name'], self.on_malformed)
            handler(data)
        except:
            logger.exception('Error in packet handling (Judge-side)')
            # You can't crash here because you aren't so sure about the judges
            # not being malicious or simply malforms. THIS IS A SERVER!

    def on_grading_begin(self, packet):
        logger.info('Grading has begun on: %s', packet['submission-id'])

    def on_grading_end(self, packet):
        logger.info('Grading has ended on: %s', packet['submission-id'])
        self._free_self(packet)

    def on_compile_error(self, packet):
        logger.info('Submission failed to compile: %s', packet['submission-id'])
        self._free_self(packet)

    def on_bad_problem(self, packet):
        logger.error('Submission referenced invalid problem "%s": %s', packet['problem'], packet['submission-id'])
        self._free_self(packet)

    def on_submission_terminated(self, packet):
        logger.info('Submission aborted: %s', packet['submission-id'])
        self._free_self(packet)

    def on_test_case(self, packet):
        logger.info('Test case completed on: %s', packet['submission-id'])

    def on_current_submission(self, packet):
        self._current_submission = packet['submission-id']
        self._current_submission_event.set()

    def on_supported_problems(self, packet):
        self._problems = packet['problems']
        self.problems = dict(self._problems)
        self.server.judges.on_got_problems(self)

    def on_malformed(self, packet):
        logger.error('Malformed packet: %s', packet)

    def on_ping_response(self, packet):
        self.latency = packet['time']
        self.load = packet['load']

    def _free_self(self, packet):
        self._working = False
        self.server.judges.on_judge_free(self, packet['submission-id'])

