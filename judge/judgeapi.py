from django.conf import settings

import socket
import struct
import json
import logging

from judge import event_poster as event

logger = logging.getLogger('judge.judgeapi')
size_pack = struct.Struct('!I')


def judge_request(packet, reply=True):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((settings.BRIDGED_DJANGO_HOST, settings.BRIDGED_DJANGO_PORT))

    output = json.dumps(packet, separators=(',', ':'))
    output = output.encode('zlib')
    writer = sock.makefile('w', 0)
    writer.write(size_pack.pack(len(output)))
    writer.write(output)
    writer.close()

    if reply:
        reader = sock.makefile('r', -1)
        input = reader.read(4)
        if not input:
            raise ValueError('Judge did not respond')
        length = size_pack.unpack(input)[0]
        input = reader.read(length)
        if not input:
            raise ValueError('Judge did not respond')
        reader.close()
        sock.close()

        input = input.decode('zlib')
        result = json.loads(input)
        return result


def judge_submission(submission):
    submission.time = None
    submission.memory = None
    submission.points = None
    submission.result = None
    submission.save()
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
        success = False
    else:
        submission.status = 'QU' if (response['name'] == 'submission-received' and
                                     response['submission-id'] == submission.id) else 'IE'

        id = 1 if submission.user.is_admin else (2 if submission.user.is_problem_setter else 0)
        event.post('submissions', {'type': 'update-submission', 'id': submission.id})
        success = True
    return success


def abort_submission(submission):
    judge_request({'name': 'terminate-submission', 'submission-id': submission.id}, reply=False)
