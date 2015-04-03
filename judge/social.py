from judge.models import Profile, Language
import logging

logger = logging.getLogger('judge.social_auth')


def make_profile(backend, user, response, *args, **kwargs):
    logger.info('Info from %s: %s', backend.name, response)

    if not hasattr(user, 'profile'):
        profile = Profile(user=user)
        profile.language = Language.get_python2()
        if backend.name == 'google-oauth2':
            profile.display_name = response['displayName']
        profile.save()
