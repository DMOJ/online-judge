import pyotp
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from judge.models import Profile


class Command(BaseCommand):
    help = 'generates or regenerates API token for user'

    def add_arguments(self, parser):
        parser.add_argument('name', help='username')

    def handle(self, *args, **options):
        token = pyotp.random_base32(length=32).lower()
        if not Profile.objects.filter(user__username=options['name']).update(api_token=token):
            raise User.DoesNotExist('User %s does not exist' % options['name'])
