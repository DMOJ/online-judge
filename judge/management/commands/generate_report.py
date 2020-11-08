import os
import shutil
import sys

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.template.loader import get_template

from judge.models import Contest, ContestParticipation
from judge.pdf_problems import DefaultPdfMaker, PhantomJSPdfMaker, PuppeteerPDFRender, SeleniumPDFRender, \
    SlimerJSPdfMaker


def generate_scoreboard(contest, period):
    problem_ids = [str(prob.id) for prob in contest.contest_problems.all().order_by('order')]
    out = ''

    for registrant in contest.registrants.all().order_by('user__user__last_name'):
        if period and int(registrant.data['class-period']) != period:
            continue

        participation = ContestParticipation.objects.filter(contest=contest, user=registrant.user).first()
        if not participation:
            continue  # joined, but didn't participate

        row = ''
        for pid in problem_ids:
            if participation.format_data and pid in participation.format_data:
                row += '<td>%.0f</td>\n' % participation.format_data[pid]['points']
            else:
                row += '<td></td>\n'
        row += '<td>%.0f</td>\n' % participation.score

        out += '<tr>\n'
        out += '<th>%s</th>\n' % registrant.user.user.get_full_name()
        out += row
        out += '</tr>\n'
    return out


class Command(BaseCommand):
    help = 'generates a report for an ICS3U contest'

    def add_arguments(self, parser):
        parser.add_argument('key', help='key of the contest to generate a report for')
        parser.add_argument('--period', type=int, help='ics3u class period of the contest')
        parser.add_argument('--dry-run', action='store_true', help="don't actually email the report")
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

        scoreboard = generate_scoreboard(contest, options['period'])
        if options['period'] is not None:
            teacher = settings.DMOJ_ICS_REPORT_PERIODS[options['period']]
        else:
            teacher = None
        with options['engine'](None, clean_up=None is None) as maker:
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
                return
            shutil.move(maker.pdffile, contest.key + '.pdf')

            if options['period'] is not None and not options['dry_run']:
                email = EmailMessage(
                    f'{contest.name} Report',
                    f'Dear {teacher["name"]},\n\nAttached are the results, '
                    'problems, and editorials for the {contest.name}.',
                    to=[teacher["email"]],
                )
                email.attach_file(contest.key + '.pdf')
                email.send()
                os.remove(contest.key + '.pdf')
