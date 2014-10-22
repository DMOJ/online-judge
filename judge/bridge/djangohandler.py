import logging
import json
import struct

from event_socket_server import ZlibPacketHandler

logger = logging.getLogger('judge.bridge')
size_pack = struct.Struct('!I')


class DjangoHandler(ZlibPacketHandler):
    def __init__(self, server, socket):
        super(DjangoHandler, self).__init__(server, socket)

        self.handlers = {
            'submission-request': self.on_submission,
            'terminate-submission': self.on_termination,
        }
        self._to_kill = True
        self.server.schedule(5, self._kill_if_no_request)

    def _kill_if_no_request(self):
        if self._to_kill:
            logger.info('Killed inactive connection: %s', self._socket.getpeername())
            self.close()

    def _format_send(self, data):
        return super(DjangoHandler, self)._format_send(json.dumps(data, separators=(',', ':')))

    def packet(self, packet):
        self._to_kill = False
        packet = json.loads(packet)
        try:
            result = self.handlers.get(packet.get('name', None), self.on_malformed)(packet)
        except:
            logger.exception('Error in packet handling (Django-facing)')
            result = {"name": "bad-request"}
        self.send(result, self._schedule_close)

    def _schedule_close(self):
        self.server.schedule(0, self.close)

    def on_submission(self, data):
        id = data['submission-id']
        problem = data['problem-id']
        language = data['language']
        source = data['source']
        self.server.judges.judge(id, problem, language, source)
        return {'name': 'submission-received', 'submission-id': id}

    def on_termination(self, data):
        try:
            self.server.judges.abort(data['submission-id'])
        except KeyError:
            return {"name": "bad-request"}

    def on_malformed(self, packet):
        logger.error('Malformed packet: %s', packet)

    def on_close(self):
        self._to_kill = False
