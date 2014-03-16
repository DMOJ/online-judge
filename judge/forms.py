from django.forms import ModelForm
from .models import Profile, Submission


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['name', 'about', 'timezone', 'language']


class ProblemSubmitForm(ModelForm):
    class Meta:
        model = Submission
        fields = ['problem', 'source', 'language']