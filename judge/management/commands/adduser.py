from django.core.management.base import BaseCommand

from judge.models import *


class Command(BaseCommand):
    help = 'creates a user'

    def add_arguments(self, parser):
        parser.add_argument('name', help='username')
        parser.add_argument('email', help='email, not necessary to be resolvable')
        parser.add_argument('language', default='PY2', help='default language ID for user')

        parser.add_argument('--superuser', action='store_true', default=False,
                            help="if specified, creates user with superuser privileges")
        parser.add_argument('--staff', action='store_true', default=False,
                            help="if specified, creates user with staff privileges")

    def handle(self, *args, **options):
        usr = User(name=options['name'], email=options['email'], is_active=True)
        usr.is_superuser = options['superuser']
        usr.is_staff = options['staff']
        usr.save()

        profile = Profile(user=usr)
        profile.language = Language.objects.get(key=options['language'])
        profile.save()
