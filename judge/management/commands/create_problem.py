from django.core.management.base import BaseCommand

from judge.models import Problem, ProblemGroup, ProblemType, Language


class Command(BaseCommand):
    help = 'create an empty problem'

    def add_arguments(self, parser):
        parser.add_argument('code', help='problem code')
        parser.add_argument('name', help='problem title')
        parser.add_argument('body', help='problem description')
        parser.add_argument('type', help='problem type')
        parser.add_argument('group', help='problem group')
        parser.add_argument('time_limit', help='time limit in (fractional) seconds')
        parser.add_argument('memory_limit', help='memory limit in kilobytes')
        parser.add_argument('points', help='problem points')
        parser.add_argument('--partial-points', help='allow partial points',
            action='store_true', default=False, dest='pr_pts')
        parser.add_argument('--all-languages', help='allow all languages',
            action='store_true', default=False, dest='all_lang')

    def handle(self, *args, **options):
        problem = Problem()
        problem.code = options['code']
        problem.name = options['name']
        problem.description = options['body']
        problem.group = ProblemGroup.objects.get(name=options['group'])
        problem.time_limit = options['time_limit']
        problem.memory_limit = options['memory_limit']
        problem.points = options['points']
        if options['pr_pts']:
            problem.partial = 1
        problem.save()

        problem.types.set([ProblemType.objects.get(name=options['type'])])
        if options['all_lang']:
            problem.allowed_languages.set(Language.objects.all())
        problem.save()
