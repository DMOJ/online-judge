import os
import shutil
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.utils import translation
from django.core.mail import EmailMessage

from judge.models import Contest
from judge.pdf_problems import DefaultPdfMaker, PhantomJSPdfMaker, PuppeteerPDFRender, SeleniumPDFRender, \
    SlimerJSPdfMaker


def generate_scoreboard(contest, period):
    # return "<div>WIP</div>"
    return ""

class Command(BaseCommand):
    help = 'generates a report for an ICS3U contest'

    def add_arguments(self, parser):
        parser.add_argument('key', help='key of the contest to generate a report for')
        parser.add_argument('--period', help='ics3u class period of the contest', type=int)
        parser.add_argument('--dry-run', help='use this option if the report should not be emailed', action='store_true')
        parser.add_argument('--directory', help='specify where to store the report')
        parser.add_argument('-p', '--phantomjs', action='store_const', const=PhantomJSPdfMaker,
                            default=DefaultPdfMaker, dest='engine')
        parser.add_argument('-s', '--slimerjs', action='store_const', const=SlimerJSPdfMaker, dest='engine')
        parser.add_argument('-c', '--chrome', '--puppeteer', action='store_const',
                            const=PuppeteerPDFRender, dest='engine')
        parser.add_argument('-S', '--selenium', action='store_const', const=SeleniumPDFRender, dest='engine')

    def handle(self, *args, **options):
        try:
            contest = Contest.objects.get(key=options['key'])
        except Contest.DoesNotExist:
            print('Bad contest code')
            return

        directory = options['directory']
        scoreboard = generate_scoreboard(contest, options['period'])
        if options['period'] != None:
            teacher = settings.DMOJ_ICS_REPORT_PERIODS[options['period']-1]
        else:
            teacher = None
        with options['engine'](directory, clean_up=directory is None) as maker:
            maker.html = get_template('contest/ics3u_report.html').render({
                'contest': contest,
                'contest_problems': contest.contest_problems.all(),
                'scoreboard': scoreboard,
                'teacher': teacher,
                'math_engine': maker.math_engine,
            }).replace('"//', '"https://').replace("'//", "'https://")
            maker.template['footerTemplate'] = "<div></div>"
            maker.title = contest.name
            for file in ('style.css', 'pygment-github.css', 'mathjax_config.js'):
                maker.load(file, os.path.join(settings.DMOJ_RESOURCES, file))
            maker.make(debug=True)
            if not maker.success:
                print(maker.log, file=sys.stderr)
            elif directory is None:
                shutil.move(maker.pdffile, contest.key + '.pdf')

            if options['period'] != None and not options['dry_run']:
                email = EmailMessage(
                    'ICS3U Contest Report',
                    f'Dear {teacher[0]},\n\nHere are the results, problems, and editorials of this week\'s ICS3U Contest.',
                    to=[teacher[1]],
                )
                email.attach_file(contest.key + '.pdf')
                email.send()
