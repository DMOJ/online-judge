import json
import logging

from judge.models import LanguageLimit
from judge.rabbitmq import connection

logger = logging.getLogger('judge.handler')


def judge_submission(submission):
    problem = submission.problem
    time, memory = problem.time_limit, problem.memory_limit
    try:
        limit = LanguageLimit.objects.get(problem=problem, language=submission.language_id)
    except LanguageLimit.DoesNotExist:
        pass
    else:
        time, memory = limit.time_limit, limit.memory_limit

    chan = connection.connect().channel()
    result = chan.queue_declare(queue='sub-%d' % submission.id)
    if not result.method.consumer_count:
        chan.basic_publish(exchange='', routing_key='submission-id', body=str(submission.id))
    language = submission.language.key
    code = problem.code
    chan.basic_publish(exchange='', routing_key='submission', body=json.dumps({
        'id': submission.id,
        'problem': code,
        'language': language,
        'source': submission.source,
        'time-limit': time,
        'memory-limit': memory,
        'short-circuit': problem.short_circuit,
    }).encode('zlib'))
    chan.close()
    logger.info('Dispatching submission: %d, language: %s, code: %s', submission.id, language, code)


def abort_submission(submission):
    chan = connection.connect().channel()
    chan.basic_publish(exchange='broadcast', routing_key='', body=json.dumps({
        'action': 'abort-submission',
        'id': submission.id,
    }).encode('zlib'))
    chan.close()
    logger.info('Abortion request: %d', submission.id)
