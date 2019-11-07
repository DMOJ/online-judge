from django.core.management.base import BaseCommand, CommandError

from judge.models import Language, LanguageLimit


class Command(BaseCommand):
    help = 'allows the problems that allow <source> to be submitted in <target>'

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

        target.problem_set.set(source.problem_set.all())
        LanguageLimit.objects.bulk_create(LanguageLimit(problem=ll.problem, language=target, time_limit=ll.time_limit,
                                                        memory_limit=ll.memory_limit)
                                          for ll in LanguageLimit.objects.filter(language=source))
