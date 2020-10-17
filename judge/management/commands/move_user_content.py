from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from judge.models import Comment, CommentVote, ContestParticipation, Profile, Submission


class Command(BaseCommand):
    help = 'moves comments and submissions from <source> to <target>'

    def add_arguments(self, parser):
        parser.add_argument('source', help='user to copy from')
        parser.add_argument('target', help='user to copy to')

    def handle(self, *args, **options):
        try:
            source = Profile.objects.get(user__username=options['source'])
        except Profile.DoesNotExist:
            raise CommandError(f'Invalid source user: {options["source"]}')

        try:
            target = Profile.objects.get(user__username=options['target'])
        except Profile.DoesNotExist:
            raise CommandError(f'Invalid target user: {options["target"]}')

        if ContestParticipation.objects.filter(user=source).exists():
            raise CommandError(f'Cannot move user {options["source"]} because it has contest participations.')

        with transaction.atomic():
            Submission.objects.filter(user=source).update(user=target)
            Comment.objects.filter(author=source).update(author=target)
            CommentVote.objects.filter(voter=source).update(voter=target)
