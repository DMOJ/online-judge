import logging
import re
from operator import itemgetter
from urllib.parse import quote

from django import forms
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from requests import HTTPError
from reversion import revisions
from social_core.backends.github import GithubOAuth2
from social_core.exceptions import InvalidEmail, SocialAuthBaseException
from social_core.pipeline.partial import partial
from social_django.middleware import SocialAuthExceptionMiddleware as OldSocialAuthExceptionMiddleware

from judge.forms import ProfileForm
from judge.models import Language, Profile

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
        emails = list(map(itemgetter(0), emails))

        if emails:
            data['email'] = emails[0]
        else:
            data['email'] = None

        return data


def slugify_username(username, renotword=re.compile(r'[^\w]')):
    return renotword.sub('', username.replace('-', '_'))


def verify_email(backend, details, *args, **kwargs):
    if not details['email']:
        raise InvalidEmail(backend)


class UsernameForm(forms.Form):
    username = forms.RegexField(regex=r'^\w+$', max_length=30, label='Username',
                                error_messages={'invalid': 'A username must contain letters, numbers, or underscores.'})

    def clean_username(self):
        if User.objects.filter(username=self.cleaned_data['username']).exists():
            raise forms.ValidationError('Sorry, the username is taken.')
        return self.cleaned_data['username']


@partial
def choose_username(backend, user, username=None, *args, **kwargs):
    if not user:
        request = backend.strategy.request
        if request.POST:
            form = UsernameForm(request.POST)
            if form.is_valid():
                return {'username': form.cleaned_data['username']}
        else:
            form = UsernameForm(initial={'username': username})
        return render(request, 'registration/username_select.html', {
            'title': 'Choose a username', 'form': form,
        })


@partial
def make_profile(backend, user, response, is_new=False, *args, **kwargs):
    if is_new:
        if not hasattr(user, 'profile'):
            profile = Profile(user=user)
            profile.language = Language.get_default_language()
            logger.info('Info from %s: %s', backend.name, response)
            profile.save()
            form = ProfileForm(instance=profile, user=user)
        else:
            data = backend.strategy.request_data()
            logger.info(data)
            form = ProfileForm(data, instance=user.profile, user=user)
            if form.is_valid():
                with revisions.create_revision(atomic=True):
                    form.save()
                    revisions.set_user(user)
                    revisions.set_comment('Updated on registration')
                    return
        return render(backend.strategy.request, 'registration/profile_creation.html', {
            'title': 'Create your profile', 'form': form,
        })


class SocialAuthExceptionMiddleware(OldSocialAuthExceptionMiddleware):
    def process_exception(self, request, exception):
        if isinstance(exception, SocialAuthBaseException):
            return HttpResponseRedirect('%s?message=%s' % (reverse('social_auth_error'),
                                                           quote(self.get_message(request, exception))))
