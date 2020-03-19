import pyotp
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from judge.models import Profile


class Command(BaseCommand):
    help = 'generates or regenerates API token for user'

    def add_arguments(self, parser):
        parser.add_argument('name', help='username')

    def handle(self, *args, **options):
        usr = User.objects.get(username=options['name'])

        # Set new API token
        profile = Profile.objects.get(user=usr)
        profile.api_token = pyotp.random_base32(length=32).lower()
        profile.save()
