import fnmatch
import json
import os
import zipfile

from celery import shared_task
from django.conf import settings
from django.utils.translation import gettext as _

from judge.models import Comment, Submission
from judge.utils.celery import Progress
from judge.utils.unicode import utf8bytes

__all__ = ('prepare_user_data',)


def apply_submission_filter(queryset, options):
    if not options['submission_download']:
        return []
    if options['submission_results']:
        queryset = queryset.filter(result__in=options['submission_results'])

    problem_code_glob_cache = {}

    def problem_code_glob_match(obj):
        code = obj.problem.code
        result = problem_code_glob_cache.get(code)
        if result is None:
            result = problem_code_glob_cache[code] = fnmatch.fnmatch(code, options['submission_problem_glob'])
        return result

    return list(filter(problem_code_glob_match, queryset))


def apply_comment_filter(queryset, options):
    if not options['comment_download']:
        return []
    return list(queryset)


@shared_task(bind=True)
def prepare_user_data(self, profile_id, options):
    options = json.loads(options)
    submissions = apply_submission_filter(Submission.objects.filter(user_id=profile_id), options)
    comments = apply_comment_filter(Comment.objects.filter(author_id=profile_id), options)
    with zipfile.ZipFile(os.path.join(settings.DMOJ_USER_DATA_CACHE, '%s.zip' % profile_id), mode='w') as data_file:
        submission_count = len(submissions)
        if submission_count:
            submission_info = {}
            with Progress(self, submission_count, stage=_('Preparing your submission data')) as p:
                prepared = 0
                interval = max(submission_count // 10, 1)
                for submission in submissions:
                    submission_info[submission.id] = {
                        'problem': submission.problem.code,
                        'date': submission.date.isoformat(),
                        'time': submission.time,
                        'memory': submission.memory,
                        'language': submission.language.key,
                        'status': submission.status,
                        'result': submission.result,
                        'case_points': submission.case_points,
                        'case_total': submission.case_total,
                    }
                    with data_file.open(
                        'submissions/%s.%s' % (submission.id, submission.language.file_extension),
                        'w',
                    ) as f:
                        f.write(utf8bytes(submission.source.source))

                    prepared += 1
                    if prepared % interval == 0:
                        p.done = prepared

                with data_file.open('submissions/info.json', 'w') as f:
                    f.write(utf8bytes(json.dumps(submission_info, sort_keys=True, indent=4)))

        comment_count = len(comments)
        if comment_count:
            comment_info = {}
            with Progress(self, comment_count, stage=_('Preparing your comment data')) as p:
                prepared = 0
                interval = max(comment_count // 10, 1)
                for comment in comments:
                    related_object = {
                        'b': 'blog post',
                        'c': 'contest',
                        'p': 'problem',
                        's': 'problem editorial',
                    }
                    comment_info[comment.id] = {
                        'date': comment.time.isoformat(),
                        'related_object': related_object[comment.page[0]],
                        'page': comment.page[2:],
                        'score': comment.score,
                    }
                    with data_file.open('comments/%s.txt' % comment.id, 'w') as f:
                        f.write(utf8bytes(comment.body))

                    prepared += 1
                    if prepared % interval == 0:
                        p.done = prepared

                with data_file.open('comments/info.json', 'w') as f:
                    f.write(utf8bytes(json.dumps(comment_info, sort_keys=True, indent=4)))

    return submission_count + comment_count
