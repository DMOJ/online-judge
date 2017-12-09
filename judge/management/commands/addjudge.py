from django.core.management.base import BaseCommand

from judge.models import Judge


class Command(BaseCommand):
    help = 'create a judge'

    def add_arguments(self, parser):
        parser.add_argument('name', help='the name of the judge')
        parser.add_argument('auth_key', help='authentication key for the judge')

    def handle(self, *args, **options):
        judge = Judge()
        judge.name = options['name']
        judge.auth_key = options['auth_key']
        judge.save()
