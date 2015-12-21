import json
import threading

from judge.models import LanguageLimit
from judge.rabbitmq import connection


_local = threading.local()


def channel():
    if hasattr(_local, 'chan'):
        return _local.chan
    chan = _local.chan = connection.connect().channel()
    return chan


def judge_submission(submission):
    problem = submission.problem
    time, memory = problem.time_limit, problem.memory_limit
    try:
        limit = LanguageLimit.objects.get(problem=problem, language=submission.language_id)
    except LanguageLimit.DoesNotExist:
        pass
    else:
        time, memory = limit.time_limit, limit.memory_limit

    chan = channel()
    result = chan.queue_declare(queue='sub-%d' % submission.id)
    if not result.method.consumer_count:
        chan.basic_publish(exchange='', routing_key='submission-id', body=str(submission.id))
    chan.basic_publish(exchange='', routing_key='submission', body=json.dumps({
        'id': submission.id,
        'problem': problem.code,
        'language': submission.language.key,
        'source': submission.source,
        'time-limit': time,
        'memory-limit': memory,
        'short-circuit': problem.short_circuit,
    }).encode('zlib'))
    chan.close()


def abort_submission(submission):
    chan = channel()
    chan.basic_publish(exchange='broadcast', routing_key='', body=json.dumps({
        'action': 'abort-submission',
        'id': submission.id,
    }).encode('zlib'))
    chan.close()
