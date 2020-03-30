from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from judge.models import Profile


class Command(BaseCommand):
    help = """Generates or regenerates an API token for user. The output is a 48 character, urlsafe base64 encoded
           token. This allows the user to access parts of the website by sending an Authorization header in the format
           of 'Bearer {token}'. Keep in mind that this token bypasses Two Factor Authentication and cannot be used to
           access admin pages."""

    def add_arguments(self, parser):
        parser.add_argument('name', help='username')

    def handle(self, *args, **options):
        try:
            print(Profile.objects.get(user__username=options['name']).generate_api_token())
        except Profile.DoesNotExist:
            raise User.DoesNotExist('User %s does not exist' % options['name'])
