from judge.models import Profile, Language
import logging

logger = logging.getLogger('judge.social_auth')


def make_profile(backend, user, response, *args, **kwargs):
    logger.info('Info from %s: %s', backend.name, response)

    if not hasattr(user, 'profile'):
        profile = Profile(user=user)
        profile.language = Language.get_python2()
        logger.info('Creating profile for %s', user.username)
        if backend.name == 'google-oauth2':
            logging.info('Using display name from %s: %s', backend.name, response['displayName'])
            profile.display_name = response['displayName']
        profile.save()
    else:
        logger.info('Already have profile: %s', user.profile)
