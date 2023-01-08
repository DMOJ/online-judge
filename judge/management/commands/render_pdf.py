import os
import shutil
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.utils import translation

from judge.models import Problem, ProblemTranslation
from judge.pdf_problems import DefaultPdfMaker, PhantomJSPdfMaker, PuppeteerPDFRender, SeleniumPDFRender, \
    SlimerJSPdfMaker


class Command(BaseCommand):
    help = 'renders a PDF file of a problem'

    def add_arguments(self, parser):
        parser.add_argument('code', help='code of problem to render')
        parser.add_argument('directory', nargs='?', help='directory to store temporaries')
        parser.add_argument('-l', '--language', default=settings.LANGUAGE_CODE,
                            help='language to render PDF in')
        parser.add_argument('-p', '--phantomjs', action='store_const', const=PhantomJSPdfMaker,
                            default=DefaultPdfMaker, dest='engine')
        parser.add_argument('-s', '--slimerjs', action='store_const', const=SlimerJSPdfMaker, dest='engine')
        parser.add_argument('-c', '--chrome', '--puppeteer', action='store_const',
                            const=PuppeteerPDFRender, dest='engine')
        parser.add_argument('-S', '--selenium', action='store_const', const=SeleniumPDFRender, dest='engine')

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

        directory = options['directory']
        with options['engine'](directory, clean_up=directory is None) as maker, \
                translation.override(options['language']):
            problem_name = problem.name if trans is None else trans.name
            maker.html = get_template('problem/raw.html').render({
                'problem': problem,
                'problem_name': problem_name,
                'description': problem.description if trans is None else trans.description,
                'url': '',
                'math_engine': maker.math_engine,
            }).replace('"//', '"https://').replace("'//", "'https://")
            maker.title = problem_name
            for file in ('style.css', 'mathjax_config.js'):
                maker.load(file, os.path.join(settings.DMOJ_RESOURCES, file))
            maker.make(debug=True)
            if not maker.success:
                print(maker.log, file=sys.stderr)
            elif directory is None:
                shutil.move(maker.pdffile, problem.code + '.pdf')
