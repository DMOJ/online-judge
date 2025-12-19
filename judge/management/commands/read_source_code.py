import json

from django.core.management.base import BaseCommand

from judge.models import SubmissionSource

BATCH_SIZE = 1000


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


class Command(BaseCommand):
    help = (
        'Reads a text file of newline-separated submission IDs and prints out '
        'the source code associated with each submission'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            type=str,
            help='Path to text file containing newline-separated submission IDs.',
        )

    def handle(self, *args, **options):
        with open(options['path'], 'r') as f:
            submission_ids = [int(s.strip()) for s in f.read().strip().splitlines()]

        for batch_ids in chunked(submission_ids, BATCH_SIZE):
            sources_by_id = dict(
                SubmissionSource.objects
                .filter(submission_id__in=batch_ids)
                .values_list('submission_id', 'source'),
            )

            for sid in batch_ids:
                self.stdout.write(json.dumps({'id': sid, 'source': sources_by_id.get(sid)}))
