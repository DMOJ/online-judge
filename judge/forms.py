from django.forms import ModelForm
from django_ace import AceWidget
from .models import Profile, Submission


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['name', 'about', 'timezone', 'language']
        widgets = {
            "text": AceWidget(theme='twilight'),
        }


class ProblemSubmitForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProblemSubmitForm, self).__init__(*args, **kwargs)
        self.fields['problem'].empty_label = None
        self.fields['language'].empty_label = None

    class Meta:
        model = Submission
        fields = ['problem', 'source', 'language']