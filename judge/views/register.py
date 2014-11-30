import re
from django import forms
from django.contrib.auth.models import User
from django.forms import CharField, ChoiceField, ModelChoiceField
from django.utils import timezone
from registration.backends.default.views import\
    RegistrationView as OldRegistrationView,\
    ActivationView as OldActivationView
from registration.forms import RegistrationForm
from judge.models import Profile, Language, Organization, TIMEZONE


valid_id = re.compile(r'^\w+$')


class CustomRegistrationForm(RegistrationForm):
    username = forms.RegexField(regex=r'^\w+$', max_length=30, label='Username',
                                error_messages={'invalid': 'A username must contain letters, numbers, or underscores'})
    display_name = CharField(max_length=50, required=False, label='Real name (optional)')
    timezone = ChoiceField(label='Location', choices=TIMEZONE)
    organization = ModelChoiceField(queryset=Organization.objects.all(), label='Organization', required=False)
    language = ModelChoiceField(queryset=Language.objects.all(), label='Preferred language', empty_label=None)

    def clean_email(self):
        if User.objects.filter(email=self.cleaned_data['email']).exists():
            raise forms.ValidationError(u'The email address "%s" is already taken. '
                                        u'Only one registration is allowed per address.' % self.cleaned_data['email'])
        return self.cleaned_data['email']


class RegistrationView(OldRegistrationView):
    title = 'Registration'
    form_class = CustomRegistrationForm
    template_name = 'registration/registration_form.jade'

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = self.title
        return super(RegistrationView, self).get_context_data(**kwargs)

    def register(self, request, **cleaned_data):
        user = super(RegistrationView, self).register(request, **cleaned_data)
        profile, _ = Profile.objects.get_or_create(user=user, defaults={
            'language': Language.get_python2()
        })
        profile.name = cleaned_data['display_name']
        profile.timezone = cleaned_data['timezone']
        profile.language = cleaned_data['language']
        profile.organization = cleaned_data['organization']
        if profile.organization is not None:
            profile.organization_join_time = timezone.now()
        profile.save()
        return user

    def get_initial(self, request=None):
        initial = super(RegistrationView, self).get_initial(request)
        initial['timezone'] = 'America/Toronto'
        initial['language'] = Language.get_python2()
        return initial


class ActivationView(OldActivationView):
    title = 'Registration'
    template_name = 'registration/activate.jade'

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = self.title
        return super(ActivationView, self).get_context_data(**kwargs)
