from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import NoArgsCommand
from django.utils import timezone
from registration.models import RegistrationProfile


class Command(NoArgsCommand):
    help = 'Delete expired user registrations from the database'

    def handle_noargs(self, **options):
        for profile in RegistrationProfile.objects.exclude(activation_key=RegistrationProfile.ACTIVATED)\
                      .filter(user__data_joined__le=timezone.now() - timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)):
            try:
                print profile.user.username
            except User.DoesNotExist:
                pass