import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.template import Context
from django.template.loader import get_template
import sys
from judge.models import Problem
from judge.pdf_problems import WebKitPdfMaker


class Command(BaseCommand):
    args = '<code> [directory]'
    help = 'reloads permissions for specified apps, or all apps if no args are specified'

    def handle(self, *args, **options):
        if not 1 <= len(args) <= 2:
            self.usage('render_pdf')
            return
        try:
            problem = Problem.objects.get(code=args[0])
        except Problem.DoesNotExist:
            print 'Bad problem code'
            return
        directory = None if len(args) < 2 else args[1]
        with WebKitPdfMaker(directory, clean_up=directory is None) as maker:
            maker.html = get_template('problem/raw.jade').render(Context({
                'problem': problem
            })).replace('"//', '"http://').replace("'//", "'http://")
            for file in ('style.css', 'pygment-github.css'):
                maker.load(file, os.path.join(settings.DMOJ_RESOURCES, file))
            maker.make(debug=True)
            if not maker.success:
                print>>sys.stderr, maker.log
            elif directory is None:
                os.rename(maker.pdffile, args[0] + '.pdf')
