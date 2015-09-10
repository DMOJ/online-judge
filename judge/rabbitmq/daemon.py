import json
import logging

from . import connection

logger = logging.getLogger('judge.handler')


class AMQPResponseDaemon(object):
    def __init__(self):
        self.chan = connection.connect().channel()
        self._judge_response_handlers = {
            'acknowledged': self.on_acknowledged,
            'grading-begin': self.on_grading_begin,
            'grading-end': self.on_grading_end,
            'compile-error': self.on_compile_error,
            'compile-message': self.on_compile_message,
            'internal-error': self.on_internal_error,
            'aborted': self.on_aborted,
            'test-case': self.on_test_case,
        }
        self._ping_handlers = {
            'ping': self.on_ping,
            'problem-update': self.on_problem_update,
            'executor-update': self.on_executor_update,
        }

    def run(self):
        self.chan.basic_consume(self._handle_judge_response, queue='judge-response')
        self.chan.basic_consume(self._handle_ping, queue='judge-ping')
        self.chan.start_consuming()

    def stop(self):
        self.chan.stop_consuming()

    def _handle_judge_response(self, chan, method, properties, body):
        try:
            packet = json.loads(body)
            self._judge_response_handlers.get(packet['name'], self.on_malformed)(packet)
            chan.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            logger.exception('Error in AMQP judge response handling')

    def _handle_ping(self, chan, method, properties, body):
        try:
            packet = json.loads(body)
            self._ping_handlers.get(packet['name'], self.on_malformed)(packet)
            chan.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            logger.exception('Error in AMQP judge ping handling')

    def on_acknowledged(self, packet):
        logger.info('Submission acknowledged: %d', packet['id'])

    def on_grading_begin(self, packet):
        logger.info('Grading has begun on: %s', packet['id'])

    def on_grading_end(self, packet):
        logger.info('Grading has ended on: %s', packet['id'])

    def on_compile_error(self, packet):
        logger.info('Submission failed to compile: %s', packet['id'])

    def on_compile_message(self, packet):
        logger.info('Submission generated compiler messages: %s', packet['id'])

    def on_internal_error(self, packet):
        try:
            raise ValueError('\n\n' + packet['message'])
        except ValueError:
            logger.exception('Judge %s failed while handling submission %s', packet['judge'], packet['id'])

    def on_aborted(self, packet):
        logger.info('Submission aborted: %s', packet['id'])

    def on_test_case(self, packet):
        logger.info('Test case completed on: %s, batch #%d', packet['id'], packet['batch'])

    def on_malformed(self, packet):
        logger.error('Malformed packet: %s', packet)

    def on_ping(self, packet):
        pass

    def on_problem_update(self, packet):
        logger.info('Judge %s updated problem list', packet['judge'])

    def on_executor_update(self, packet):
        logger.info('Judge %s updated executor list', packet['judge'])
