from django.core.management.base import BaseCommand
from judge.models import Problem, ProblemGroup, ProblemType


class Command(BaseCommand):
    args = '<code> <name> <body> <type> <group>'
    help = 'create an empty problem'

    def handle(self, *args, **options):
        if len(args) != 5:
            self.usage('create_problem')
        code, name, body, type, group = args
        problem = Problem()
        problem.code = code
        problem.name = name
        problem.description = body
        problem.group = ProblemGroup.objects.get(name=group)
        problem.types = [ProblemType.objects.get(name=type)]
        problem.save()
