from django.core.management.base import BaseCommand

from judge.models import Problem, ProblemGroup, ProblemType


class Command(BaseCommand):
    help = 'create an empty problem'

    def add_arguments(self, parser):
        parser.add_argument('code', help='problem code')
        parser.add_argument('name', help='problem title')
        parser.add_argument('body', help='problem description')
        parser.add_argument('type', help='problem type')
        parser.add_argument('group', help='problem group')

    def handle(self, *args, **options):
        problem = Problem()
        problem.code = options['code']
        problem.name = options['name']
        problem.description = options['body']
        problem.group = ProblemGroup.objects.get(name=options['group'])
        problem.types = [ProblemType.objects.get(name=options['type'])]
        problem.save()
