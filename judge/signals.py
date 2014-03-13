from django.dispatch import receiver
from registration.signals import user_activated
from .models import Profile


@receiver(user_activated)
def make_profile(sender, user, **kwargs):
    Profile.objects.get_or_create(user=user)
