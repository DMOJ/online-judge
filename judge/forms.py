from operator import attrgetter

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import ModelForm

from django_ace import AceWidget
from judge.comments import valid_comment_page
from judge.models import Organization, Profile, Submission, Comment, Problem
from judge.widgets import MathJaxPagedownWidget, PagedownWidget


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['name', 'about', 'organization', 'timezone', 'language', 'ace_theme']


class ProblemSubmitForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProblemSubmitForm, self).__init__(*args, **kwargs)
        self.fields['problem'].empty_label = None
        self.fields['problem'].widget = forms.HiddenInput()
        self.fields['language'].empty_label = None
        self.fields['language'].label_from_instance = attrgetter('display_name')

    class Meta:
        model = Submission
        fields = ['problem', 'source', 'language']
        widgets = {
            'source': AceWidget(theme='twilight'),
        }


class OrganizationForm(ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'key', 'about']


class EditOrganizationForm(ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'short_name', 'about', 'admins']
        widgets = {
            'admins': FilteredSelectMultiple('Admins', False)
        }
        if PagedownWidget is not None:
            widgets['about'] = MathJaxPagedownWidget


class NewOrganizationForm(EditOrganizationForm):
    class Meta(EditOrganizationForm.Meta):
        fields = ['key'] + EditOrganizationForm.Meta.fields


class ProblemEditForm(ModelForm):
    class Meta:
        model = Problem
        fields = ['name', 'is_public', 'authors', 'types', 'group', 'description', 'time_limit',
                  'memory_limit', 'points', 'partial', 'allowed_languages']
        widgets = {
            'authors': FilteredSelectMultiple('creators', False),
            'types': FilteredSelectMultiple('types', False),
            'allowed_languages': FilteredSelectMultiple('languages', False),
        }
        if MathJaxPagedownWidget is not None:
            widgets['description'] = MathJaxPagedownWidget

    def __init__(self, *args, **kwargs):
        super(ProblemEditForm, self).__init__(*args, **kwargs)
        self.fields['authors'].queryset = Profile.objects.filter(Q(user__groups__name__in=['ProblemSetter', 'Admin']) |
                                                                 Q(user__is_superuser=True))
