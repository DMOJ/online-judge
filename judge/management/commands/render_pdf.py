from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.utils import translation

from judge.models import Problem, ProblemTranslation
from judge.utils.pdfoid import render_pdf


class Command(BaseCommand):
    help = 'renders a PDF file of a problem'

    def add_arguments(self, parser):
        parser.add_argument('code', help='code of problem to render')
        parser.add_argument('-l', '--language', default=settings.LANGUAGE_CODE,
                            help='language to render PDF in')

    def handle(self, *args, **options):
        try:
            problem = Problem.objects.get(code=options['code'])
        except Problem.DoesNotExist:
            print('Bad problem code')
            return

        try:
            trans = problem.translations.get(language=options['language'])
        except ProblemTranslation.DoesNotExist:
            trans = None

        with open(problem.code + '.pdf', 'wb') as f, translation.override(options['language']):
            problem_name = problem.name if trans is None else trans.name
            f.write(render_pdf(
                html=get_template('problem/raw.html').render({
                    'problem': problem,
                    'problem_name': problem_name,
                    'description': problem.description if trans is None else trans.description,
                    'url': '',
                }).replace('"//', '"https://').replace("'//", "'https://"),
                title=problem_name,
            ))
