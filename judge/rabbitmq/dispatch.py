import json
from judge.rabbitmq import connection


def judge_submission(submission):
    chan = connection.conn.channel()
    chan.basic_publish(exchange='', routing_key='submission', body=json.dumps({
        'id': submission.id,
        'problem': submission.problem.code,
        'language': submission.language.key,
        'source': submission.source
    }))
