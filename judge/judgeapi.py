from django.conf import settings

import socket
import json
import logging

logger = logging.getLogger('judge.judgeapi')


def judge_request(packet):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((settings.BRIDGED_DJANGO_HOST, settings.BRIDGED_DJANGO_PORT))

    output = json.dumps(packet, separators=(',', ':'))
    output = output.encode('zlib')
    writer = sock.makefile('w', 0)
    writer.write(output)
    writer.close()

    reader = sock.makefile('r', -1)
    input = reader.read()
    reader.close()
    sock.close()

    input = input.decode('zlib')
    result = json.loads(input)
    return result


def judge_submission(submission):
    try:
        response = judge_request({
            'name': 'submission-request',
            'submission-id': submission.id,
            'problem-id': submission.problem.code,
            'language': submission.language.key,
            'source': submission.source,
        })
    except BaseException:
        logger.exception('Failed to send request to judge')
        submission.status = 'IE'
        submission.save()
    else:
        submission.status = 'QU' if (response['name'] == 'submission-received' and
                                     response['submission-id'] == submission.id) else 'IE'
        submission.save()
