import logging
import socket
import SocketServer
import struct
import json
import threading

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
        }
        self._current_submission = None
        self._current_submission_event = threading.Event()
        self._load = set()
        logger.info('Judge connected from: %s', self.client_address)
        self.server.judges.append(self)

    def finish(self):
        SocketServer.StreamRequestHandler.finish(self)
        logger.info('Judge disconnected from: %s', self.client_address)
        self.server.judges.remove(self)

    def handle(self):
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
    def load(self):
        return len(self._load)

    def submit(self, id, problem, language, source):
        packet = {
            'name': 'submission-request',
            'submission-id': id,
            'problem-id': problem,
            'language': language,
            'source': source,
        }
        self._send(packet)
        self._load.add(id)

    def get_current_submission(self):
        self._send({'name': 'get-current-submission'})
        self._current_submission_event.wait()
        self._current_submission_event.clear()
        return self._current_submission

    def _send(self, data):
        data = json.dumps(data, separators=(',', ':'))
        compress = data.encode('zlib')
        self.wfile.write(size_pack.pack(len(compress)))
        self.wfile.write(compress)

    def _packet(self, data):
        try:
            if 'name' not in data:
                self.on_malformed(data)
            handler = self.handlers.get(data['name'], JudgeHandler.on_malformed)
            handler(data)
            if data['name'] in ('grading-end', 'compile-error') and 'submission-id' in data:
                self._load.remove(data['submission-id'])
        except:
            logger.exception('Error in packet handling (Judge-side)')
            # You can't crash here because you aren't so sure about the judges
            # not being malicious or simply malforms. THIS IS A SERVER!

    def on_grading_begin(self, packet):
        logger.info('Grading has begun on: %s', packet['submission-id'])

    def on_grading_end(self, packet):
        logger.info('Grading has ended on: %s', packet['submission-id'])

    def on_compile_error(self, packet):
        logger.info('Submission failed to compile: %s', packet['submission-id'])

    def on_bad_problem(self, packet):
        logger.error('Submission referenced invalid problem "%s": %s', packet['problem'], packet['submission-id'])

    def on_test_case(self, packet):
        logger.info('Test case completed on: %s', packet['submission-id'])

    def on_current_submission(self, packet):
        self._current_submission = packet['submission-id']
        self._current_submission_event.set()

    def on_malformed(self, packet):
        logger.error('Malformed packet: %s', packet)

