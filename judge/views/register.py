import re

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.forms import CharField, ChoiceField, ModelChoiceField
from django.shortcuts import render
from registration.backends.default.views import\
    RegistrationView as OldRegistrationView,\
    ActivationView as OldActivationView
from registration.forms import RegistrationForm
from sortedm2m.forms import SortedMultipleChoiceField

from judge.models import Profile, Language, Organization, TIMEZONE


valid_id = re.compile(r'^\w+$')


class CustomRegistrationForm(RegistrationForm):
    username = forms.RegexField(regex=r'^\w+$', max_length=30, label='Username',
                                error_messages={'invalid': 'A username must contain letters, numbers, or underscores'})
    display_name = CharField(max_length=50, required=False, label='Real name (optional)')
    timezone = ChoiceField(label='Location', choices=TIMEZONE)
    organizations = SortedMultipleChoiceField(queryset=Organization.objects.filter(is_open=True),
                                              label='Organizations', required=False)
    language = ModelChoiceField(queryset=Language.objects.all(), label='Preferred language', empty_label=None)

    def clean_email(self):
        if User.objects.filter(email=self.cleaned_data['email']).exists():
            raise forms.ValidationError(u'The email address "%s" is already taken. '
                                        u'Only one registration is allowed per address.' % self.cleaned_data['email'])
        if '@' in self.cleaned_data['email'] and \
                  self.cleaned_data['email'].split('@')[-1] in getattr(settings, 'BAD_MAIL_PROVIDERS', set()):
            raise forms.ValidationError(u'Your email provider is not allowed due to history of abuse. '
                                        u'Please use a reputable email provider.')
        return self.cleaned_data['email']


class RegistrationView(OldRegistrationView):
    title = 'Registration'
    form_class = CustomRegistrationForm
    template_name = 'registration/registration_form.jade'

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = self.title
        tzmap = getattr(settings, 'TIMEZONE_MAP', None)
        kwargs['TIMEZONE_MAP'] = tzmap or 'http://momentjs.com/static/img/world.png'
        kwargs['TIMEZONE_BG'] = getattr(settings, 'TIMEZONE_BG', None if tzmap else '#4E7CAD')
        return super(RegistrationView, self).get_context_data(**kwargs)

    def register(self, *args, **cleaned_data):
        user = super(RegistrationView, self).register(*args, **cleaned_data)
        profile, _ = Profile.objects.get_or_create(user=user, defaults={
            'language': Language.get_python2()
        })
        profile.name = cleaned_data['display_name']
        profile.timezone = cleaned_data['timezone']
        profile.language = cleaned_data['language']
        profile.organizations.add(*cleaned_data['organizations'])
        profile.save()
        return user

    def get_initial(self, request=None):
        initial = super(RegistrationView, self).get_initial(request)
        initial['timezone'] = getattr(settings, 'DEFAULT_USER_TIME_ZONE', 'America/Toronto')
        initial['language'] = Language.get_python2()
        return initial


class ActivationView(OldActivationView):
    title = 'Registration'
    template_name = 'registration/activate.jade'

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = self.title
        return super(ActivationView, self).get_context_data(**kwargs)


def social_auth_error(request):
    return render(request, 'generic_message.jade', {
        'title': 'Authentication failure',
        'message': request.GET.get('message')
    })