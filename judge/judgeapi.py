import json
import logging
import socket
import struct
import zlib
from operator import attrgetter

from django.conf import settings
from django.db import transaction
from django.db.models import BooleanField, F, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from judge import event_poster as event
from judge.judge_priority import BATCH_REJUDGE_PRIORITY, CONTEST_SUBMISSION_PRIORITY, DEFAULT_PRIORITY, REJUDGE_PRIORITY

logger = logging.getLogger('judge.judgeapi')
size_pack = struct.Struct('!I')


def _post_update_submission(submission, done=False):
    if submission.problem.is_public:
        event.post('submissions', {'type': 'done-submission' if done else 'update-submission',
                                   'id': submission.id,
                                   'contest': submission.contest_key,
                                   'user': submission.user_id, 'problem': submission.problem_id,
                                   'status': submission.status, 'language': submission.language.key})


def judge_request(packet, reply=True):
    sock = socket.create_connection(settings.BRIDGED_DJANGO_CONNECT or
                                    settings.BRIDGED_DJANGO_ADDRESS[0])

    output = json.dumps(packet, separators=(',', ':'))
    output = zlib.compress(output.encode('utf-8'))
    writer = sock.makefile('wb')
    writer.write(size_pack.pack(len(output)))
    writer.write(output)
    writer.close()

    if reply:
        reader = sock.makefile('rb', -1)
        input = reader.read(size_pack.size)
        if not input:
            raise ValueError('Judge did not respond')
        length = size_pack.unpack(input)[0]
        input = reader.read(length)
        if not input:
            raise ValueError('Judge did not respond')
        reader.close()
        sock.close()

        result = json.loads(zlib.decompress(input).decode('utf-8'))
        return result


def judge_submission(submission, rejudge=False, judge_id=None):
    from .models import ContestSubmission, Submission, SubmissionTestCase

    updates = {'time': None, 'memory': None, 'points': None, 'result': None, 'case_points': 0, 'case_total': 0,
               'error': None, 'rejudged_date': timezone.now() if rejudge else None, 'status': 'QU'}
    try:
        # This is set proactively; it might get unset in judgecallback's on_grading_begin if the problem doesn't
        # actually have pretests stored on the judge.
        updates['is_pretested'] = all(ContestSubmission.objects.filter(submission=submission)
                                      .values_list('problem__contest__run_pretests_only', 'problem__is_pretested')[0])
    except IndexError:
        priority = DEFAULT_PRIORITY
    else:
        priority = CONTEST_SUBMISSION_PRIORITY

    # This should prevent double rejudge issues by permitting only the judging of
    # QU (which is the initial state) and D (which is the final state).
    # Even though the bridge will not queue a submission already being judged,
    # we will destroy the current state by deleting all SubmissionTestCase objects.
    # However, we can't drop the old state immediately before a submission is set for judging,
    # as that would prevent people from knowing a submission is being scheduled for rejudging.
    # It is worth noting that this mechanism does not prevent a new rejudge from being scheduled
    # while already queued, but that does not lead to data corruption.
    if not Submission.objects.filter(id=submission.id).exclude(status__in=('P', 'G')).update(**updates):
        return False

    SubmissionTestCase.objects.filter(submission_id=submission.id).delete()

    try:
        response = judge_request({
            'name': 'submission-request',
            'submission-id': submission.id,
            'problem-id': submission.problem.code,
            'language': submission.language.key,
            'source': submission.source.source,
            'judge-id': judge_id,
            'priority': REJUDGE_PRIORITY if rejudge else priority,
        })
    except BaseException:
        logger.exception('Failed to send request to judge')
        Submission.objects.filter(id=submission.id).update(status='IE', result='IE')
        success = False
    else:
        if response['name'] != 'submission-received' or response['submission-id'] != submission.id:
            Submission.objects.filter(id=submission.id).update(status='IE', result='IE')
        _post_update_submission(submission)
        success = True
    return success


def batch_judge_submission(submissions, rejudge=False, judge_id=None):
    from .models import Submission, SubmissionTestCase
    updates = {
        'time': None, 'memory': None, 'points': None, 'result': None, 'case_points': 0, 'case_total': 0,
        'error': None, 'rejudged_date': timezone.now() if rejudge else None, 'status': 'QU',
        'is_pretested': Coalesce(
            Subquery(
                Submission.objects.filter(pk=OuterRef('pk'))
                .annotate(pretested=F('contest_object__run_pretests_only').bitand(F('contest__problem__is_pretested')))
                .values_list('pretested')[:1],
                output_field=BooleanField(),
            ),
            False,
        ),
    }

    with transaction.atomic():
        submission_queryset = Submission.objects.filter(id__in=map(attrgetter('id'), submissions)) \
                                                .exclude(status__in=('P', 'G'))
        submission_queryset.update(**updates)

        ids = set(submission_queryset.values_list('id', flat=True))
        # Do the filtering using the new set of IDs rather than submission_queryset
        # because submission_queryset itself takes a list of IDs anyways.
        SubmissionTestCase.objects.filter(submission_id__in=ids).delete()

    submissions = [submission for submission in submissions if submission.id in ids]

    try:
        response = judge_request({
            'name': 'batch-submission-request',
            'submissions': [{
                'submission-id': submission.id,
                'problem-id': submission.problem.code,
                'language': submission.language.key,
                'source': submission.source.source,
                'priority': BATCH_REJUDGE_PRIORITY if rejudge else (
                    CONTEST_SUBMISSION_PRIORITY if submission.contest_object is not None else DEFAULT_PRIORITY
                )
            } for submission in submissions],
            'judge-id': judge_id,
        })
    except BaseException:
        logger.exception('Failed to send request to judge')
        processed_ids = set()
    else:
        processed_ids = set(response['submission-ids']) if 'submission-ids' in response else set()

    if processed_ids != ids:
        Submission.objects.filter(id__in=ids - processed_ids).update(status='IE', result='IE', error='')

    for submission in submissions:
        # If the submission is not in processed_ids, that means the submission IE'd and thus is "done" judging.
        _post_update_submission(submission, done=submission.id not in processed_ids)


def disconnect_judge(judge, force=False):
    judge_request({'name': 'disconnect-judge', 'judge-id': judge.name, 'force': force}, reply=False)


def update_disable_judge(judge):
    judge_request({'name': 'disable-judge', 'judge-id': judge.name, 'is-disabled': judge.is_disabled})


def abort_submission(submission):
    from .models import Submission
    # We only want to try to abort a submission if it's still grading, otherwise this can lead to fully graded
    # submissions marked as aborted.
    if submission.status == 'D':
        return
    response = judge_request({'name': 'terminate-submission', 'submission-id': submission.id})
    # This defaults to true, so that in the case the JudgeList fails to remove the submission from the queue,
    # and returns a bad-request, the submission is not falsely shown as "Aborted" when it will still be judged.
    if not response.get('judge-aborted', True):
        Submission.objects.filter(id=submission.id).update(status='AB', result='AB', points=0)
        event.post('sub_%s' % Submission.get_id_secret(submission.id), {'type': 'aborted'})
        _post_update_submission(submission, done=True)
