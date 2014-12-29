from django.core.management.base import BaseCommand, CommandError
from judge.models import Language


class Command(BaseCommand):
    args = '<source> <target>'
    help = 'allows the problems allowed to be submitted in the <source> language to be submitted in <target> language'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError('Usage: python manage.py copy_language <source> <target>')
        source, target = args
        try:
            source = Language.objects.get(key=source)
        except Language.DoesNotExist:
            raise CommandError('Invalid source language: %s', source)
        try:
            target = Language.objects.get(key=target)
        except Language.DoesNotExist:
            raise CommandError('Invalid target language: %s', source)
        target.problem_set.add(*source.problem_set.all())