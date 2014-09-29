from django.forms import CharField, ChoiceField, ModelChoiceField
from registration.backends.default.views import\
    RegistrationView as OldRegistrationView,\
    ActivationView as OldActivationView
from registration.forms import RegistrationForm
from judge.models import Profile, Language, TIMEZONE


class CustomRegistrationForm(RegistrationForm):
    display_name = CharField(max_length=50, required=False, label='Display name (optional)')
    timezone = ChoiceField(choices=TIMEZONE)
    language = ModelChoiceField(queryset=Language.objects.all(), label='Default language', required=True)


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
