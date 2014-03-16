from django.core.exceptions import MiddlewareNotUsed
from judge.models import Profile, Language
from django.contrib.auth.models import User


class InitializationMiddleware(object):
    def __init__(self):
        lang = Language.objects.get_or_create(key='PY2', name='Python 2')[0]  # Create a default language
        for user in User.objects.filter(profile=None):
            # These poor profileless users
            profile = Profile(user=user, language=lang)
            profile.save()
        raise MiddlewareNotUsed