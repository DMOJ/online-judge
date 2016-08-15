import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template import Context
from django.template.loader import get_template
from django.utils import translation

from judge.models import Problem, ProblemTranslation
from judge.pdf_problems import WebKitPdfMaker


class Command(BaseCommand):
    help = 'renders a PDF file of a problem'

    def add_arguments(self, parser):
        parser.add_argument('code', help='code of problem to render')
        parser.add_argument('directory', nargs='?', help='directory to store temporaries')
        parser.add_argument('-l', '--language', default=settings.LANGUAGE_CODE,
                            help='language to render PDF in')

    def handle(self, *args, **options):
        try:
            problem = Problem.objects.get(code=options['code'])
        except Problem.DoesNotExist:
            print 'Bad problem code'
            return

        problem = self.get_object()
        try:
            trans = problem.translations.get(language=options['language'])
        except ProblemTranslation.DoesNotExist:
            trans = None

        directory = options['directory']
        with WebKitPdfMaker(directory, clean_up=directory is None) as maker, \
                translation.override(options['language']):
            maker.html = get_template('problem/raw.jade').render(Context({
                'problem': problem,
                'problem_name': problem.name if trans is None else trans.name,
                'description': problem.description if trans is None else trans.description,
            })).replace('"//', '"http://').replace("'//", "'http://")
            for file in ('style.css', 'pygment-github.css'):
                maker.load(file, os.path.join(settings.DMOJ_RESOURCES, file))
            maker.make(debug=True)
            if not maker.success:
                print>>sys.stderr, maker.log
            elif directory is None:
                os.rename(maker.pdffile, problem.code + '.pdf')
