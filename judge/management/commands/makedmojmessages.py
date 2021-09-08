import glob
import io
import os
import sys

from django.conf import settings
from django.core.management import CommandError
from django.core.management.commands.makemessages import Command as MakeMessagesCommand, check_programs

from judge.models import NavigationBar, ProblemType


class Command(MakeMessagesCommand):
    def add_arguments(self, parser):
        parser.add_argument('--locale', '-l', default=[], dest='locale', action='append',
                            help='Creates or updates the message files for the given locale(s) (e.g. pt_BR). '
                                 'Can be used multiple times.')
        parser.add_argument('--exclude', '-x', default=[], dest='exclude', action='append',
                            help='Locales to exclude. Default is none. Can be used multiple times.')
        parser.add_argument('--all', '-a', action='store_true', dest='all',
                            default=False, help='Updates the message files for all existing locales.')
        parser.add_argument('--no-wrap', action='store_true', dest='no_wrap',
                            default=False, help="Don't break long message lines into several lines.")
        parser.add_argument('--no-obsolete', action='store_true', dest='no_obsolete',
                            default=False, help='Remove obsolete message strings.')
        parser.add_argument('--keep-pot', action='store_true', dest='keep_pot',
                            default=False, help='Keep .pot file after making messages. Useful when debugging.')

    def handle(self, *args, **options):
        locale = options.get('locale')
        exclude = options.get('exclude')
        self.domain = 'dmoj-user'
        self.verbosity = options.get('verbosity')
        process_all = options.get('all')

        # Need to ensure that the i18n framework is enabled
        if settings.configured:
            settings.USE_I18N = True
        else:
            settings.configure(USE_I18N=True)

        # Avoid messing with mutable class variables
        if options.get('no_wrap'):
            self.msgmerge_options = self.msgmerge_options[:] + ['--no-wrap']
            self.msguniq_options = self.msguniq_options[:] + ['--no-wrap']
            self.msgattrib_options = self.msgattrib_options[:] + ['--no-wrap']
            self.xgettext_options = self.xgettext_options[:] + ['--no-wrap']
        if options.get('no_location'):
            self.msgmerge_options = self.msgmerge_options[:] + ['--no-location']
            self.msguniq_options = self.msguniq_options[:] + ['--no-location']
            self.msgattrib_options = self.msgattrib_options[:] + ['--no-location']
            self.xgettext_options = self.xgettext_options[:] + ['--no-location']

        self.no_obsolete = options.get('no_obsolete')
        self.keep_pot = options.get('keep_pot')

        if locale is None and not exclude and not process_all:
            raise CommandError("Type '%s help %s' for usage information." % (
                os.path.basename(sys.argv[0]), sys.argv[1]))

        self.invoked_for_django = False
        self.locale_paths = []
        self.default_locale_path = None
        if os.path.isdir(os.path.join('conf', 'locale')):
            self.locale_paths = [os.path.abspath(os.path.join('conf', 'locale'))]
            self.default_locale_path = self.locale_paths[0]
            self.invoked_for_django = True
        else:
            self.locale_paths.extend(settings.LOCALE_PATHS)
            # Allow to run makemessages inside an app dir
            if os.path.isdir('locale'):
                self.locale_paths.append(os.path.abspath('locale'))
            if self.locale_paths:
                self.default_locale_path = self.locale_paths[0]
                if not os.path.exists(self.default_locale_path):
                    os.makedirs(self.default_locale_path)

        # Build locale list
        locale_dirs = list(filter(os.path.isdir, glob.glob('%s/*' % self.default_locale_path)))
        all_locales = list(map(os.path.basename, locale_dirs))

        # Account for excluded locales
        if process_all:
            locales = all_locales
        else:
            locales = locale or all_locales
            locales = set(locales) - set(exclude)

        if locales:
            check_programs('msguniq', 'msgmerge', 'msgattrib')

        check_programs('xgettext')

        try:
            potfiles = self.build_potfiles()

            # Build po files for each selected locale
            for locale in locales:
                if self.verbosity > 0:
                    self.stdout.write('processing locale %s\n' % locale)
                for potfile in potfiles:
                    self.write_po_file(potfile, locale)
        finally:
            if not self.keep_pot:
                self.remove_potfiles()

    def find_files(self, root):
        return []

    def _emit_message(self, potfile, string):
        potfile.write("""
msgid "%s"
msgstr ""
""" % string.replace('\\', r'\\').replace('\t', '\\t').replace('\n', '\\n').replace('"', '\\"'))

    def process_files(self, file_list):
        with io.open(os.path.join(self.default_locale_path, 'dmoj-user.pot'), 'w', encoding='utf-8') as potfile:
            if self.verbosity > 1:
                self.stdout.write('processing navigation bar')
            for label in NavigationBar.objects.values_list('label', flat=True):
                if self.verbosity > 2:
                    self.stdout.write('processing navigation item label "%s"\n' % label)
                self._emit_message(potfile, label)

            if self.verbosity > 1:
                self.stdout.write('processing problem types')
            for name in ProblemType.objects.values_list('full_name', flat=True):
                if self.verbosity > 2:
                    self.stdout.write('processing problem type name "%s"\n' % name)
                self._emit_message(potfile, name)
