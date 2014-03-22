from django.conf import settings

import socket
import struct
import json
import logging

from judge.simple_comet_client import delete_channel, create_channel, send_message

logger = logging.getLogger('judge.judgeapi')
size_pack = struct.Struct('!I')


def judge_request(packet):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((settings.BRIDGED_DJANGO_HOST, settings.BRIDGED_DJANGO_PORT))

    output = json.dumps(packet, separators=(',', ':'))
    output = output.encode('zlib')
    writer = sock.makefile('w', 0)
    writer.write(size_pack.pack(len(output)))
    writer.write(output)
    writer.close()

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
    chan = 'sub_%d' % submission.id
    delete_channel(chan) # Delete if exist
    create_channel(chan)
    create_channel('submissions')  #TODO: only attempt to create once
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

        send_message('submissions', 'submission-start %d %s %s %s' % (submission.id, submission.status, submission.language.key, submission.user.user.username))
        success = True
    submission.time = None
    submission.memory = None
    submission.points = None
    submission.result = None
    submission.save()
    return success
