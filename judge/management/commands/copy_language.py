from django.core.management.base import BaseCommand, CommandError

from judge.models import Language


class Command(BaseCommand):
    help = 'allows the problems allowed to be submitted in the <source> language to be submitted in <target> language'

    def add_arguments(self, parser):
        parser.add_argument('source', help='language to copy from')
        parser.add_argument('target', help='language to copy to')

    def handle(self, *args, **options):
        try:
            source = Language.objects.get(key=options['source'])
        except Language.DoesNotExist:
            raise CommandError('Invalid source language: %s' % options['source'])

        try:
            target = Language.objects.get(key=options['target'])
        except Language.DoesNotExist:
            raise CommandError('Invalid target language: %s' % options['target'])

        target.problem_set = source.problem_set.all()