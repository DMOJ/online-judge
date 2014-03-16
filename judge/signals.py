from django.dispatch import receiver
from registration.signals import user_registered
from .models import Profile, Language


@receiver(user_registered)
def make_profile(sender, user, **kwargs):
    Profile.objects.get_or_create(user=user,
                                  language=Language.objects.get_or_create(key='PY2', name='Python 2')[0])
