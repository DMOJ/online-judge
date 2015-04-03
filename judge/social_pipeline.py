import logging
from operator import itemgetter

from django.db import transaction
from django.shortcuts import render_to_response
from django.template import RequestContext
from requests import HTTPError
import reversion
from social.backends.github import GithubOAuth2
from social.exceptions import InvalidEmail
from social.pipeline.partial import partial

from judge.forms import ProfileForm
from judge.models import Profile, Language


logger = logging.getLogger('judge.social_auth')


class GitHubSecureEmailOAuth2(GithubOAuth2):
    def user_data(self, access_token, *args, **kwargs):
        data = self._user_data(access_token)
        try:
            emails = self._user_data(access_token, '/emails')
        except (HTTPError, ValueError, TypeError):
            emails = []

        emails = [(e, e.get('primary'), False) for e in emails if isinstance(e, dict) and e.get('verified')]
        emails.sort(key=itemgetter(1), reverse=True)
        emails = map(itemgetter(0), emails)

        if emails:
            data['email'] = emails[0]
        else:
            data['email'] = None


def verify_email(backend, details, *args, **kwargs):
    if not details['email']:
        raise InvalidEmail(backend)


@partial
def make_profile(backend, user, response, is_new=False, *args, **kwargs):
    logger.info('Info from %s: %s', backend.name, response)

    if is_new:
        if not hasattr(user, 'profile'):
            profile = Profile(user=user)
            profile.language = Language.get_python2()
            logger.info('Creating profile for %s', user.username)
            if backend.name == 'google-oauth2':
                logger.info('Using display name from %s: %s', backend.name, response['displayName'])
                profile.name = response['displayName']
            elif backend.name == 'github' and 'name' in response:
                logger.info('Using display name from %s: %s', backend.name, response['name'])
                profile.name = response['name']
            profile.save()
            form = ProfileForm(instance=profile)
        else:
            data = backend.strategy.request_data()
            logger.info(data)
            form = ProfileForm(data, instance=user.profile)
            if form.is_valid():
                with transaction.atomic(), reversion.create_revision():
                    form.save()
                    reversion.set_user(user)
                    reversion.set_comment('Updated on registration')
                    return
        return render_to_response('registration/profile_creation.jade', {'form': form},
                                  context_instance=RequestContext(backend.strategy.request))
