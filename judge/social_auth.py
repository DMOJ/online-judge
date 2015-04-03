import logging
from operator import itemgetter
from urllib import quote

from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from requests import HTTPError
import reversion
from social.apps.django_app.middleware import SocialAuthExceptionMiddleware as OldSocialAuthExceptionMiddleware
from social.backends.github import GithubOAuth2
from social.exceptions import InvalidEmail, SocialAuthBaseException
from social.pipeline.partial import partial

from judge.forms import ProfileForm
from judge.models import Profile, Language


logger = logging.getLogger('judge.social_auth')


class GitHubSecureEmailOAuth2(GithubOAuth2):
    name = 'github-secure'

    def user_data(self, access_token, *args, **kwargs):
        data = self._user_data(access_token)
        try:
            emails = self._user_data(access_token, '/emails')
        except (HTTPError, ValueError, TypeError):
            emails = []

        emails = [(e.get('email'), e.get('primary'), 0) for e in emails if isinstance(e, dict) and e.get('verified')]
        emails.sort(key=itemgetter(1), reverse=True)
        emails = map(itemgetter(0), emails)

        if emails:
            data['email'] = emails[0]
        else:
            data['email'] = None

        return data


def verify_email(backend, details, *args, **kwargs):
    if not details['email']:
        raise InvalidEmail(backend)


@partial
def make_profile(backend, user, response, is_new=False, *args, **kwargs):
    if is_new:
        if not hasattr(user, 'profile'):
            profile = Profile(user=user)
            profile.language = Language.get_python2()
            if backend.name == 'google-oauth2':
                profile.name = response['displayName']
            elif backend.name == 'github' and 'name' in response:
                profile.name = response['name']
            else:
                logger.info('Info from %s: %s', backend.name, response)
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
        return render(backend.strategy.request, 'registration/profile_creation.jade', {'form': form})


class SocialAuthExceptionMiddleware(OldSocialAuthExceptionMiddleware):
    def process_exception(self, request, exception):
        if isinstance(exception, SocialAuthBaseException):
            return HttpResponseRedirect('%s?message=%s' % (reverse('social_auth_error'),
                                                           quote(self.get_message(request, exception))))