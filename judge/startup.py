from django.db.models.signals import post_migrate
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db import DatabaseError

def hook_post_migrate():
    post_migrate.connect(create_missing_profiles, dispatch_uid="judge.create_missing_profiles")

@receiver(post_migrate)
def create_missing_profiles(sender, **kwargs):
    from judge.models import Language, Profile

    try:
        lang = Language.get_default_language()
        users = User.objects.filter(profile=None)
        for user in users:
            Profile.objects.create(user=user, language=lang)
    except DatabaseError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Profile creation failed during post_migrate: %s", e)
