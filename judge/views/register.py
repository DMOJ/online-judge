from django.forms import CharField
from registration.backends.default.views import\
    RegistrationView as OldRegistrationView,\
    ActivationView as OldActivationView
from registration.forms import RegistrationForm
from judge.models import Profile, Language


class CustomRegistrationForm(RegistrationForm):
    display_name = CharField(max_length=50, required=False)


class RegistrationView(OldRegistrationView):
    title = 'Registration'
    form_class = CustomRegistrationForm

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = self.title
        return super(RegistrationView, self).get_context_data(**kwargs)

    def register(self, request, **cleaned_data):
        user = super(RegistrationView, self).register(request, **cleaned_data)
        profile, _ = Profile.objects.get_or_create(user=user, defaults={
            'language': Language.objects.get_or_create(key='PY2', name='Python 2')[0]
        })
        profile.name = cleaned_data['display_name']
        profile.save()
        return user


class ActivationView(OldActivationView):
    title = 'Registration'

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = self.title
        return super(ActivationView, self).get_context_data(**kwargs)
