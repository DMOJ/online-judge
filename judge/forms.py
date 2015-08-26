from operator import attrgetter

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.forms import ModelForm, CharField, TextInput

from django_ace import AceWidget
from judge.models import Organization, Profile, Submission, Problem, PrivateMessage, fix_unicode, Language
from judge.widgets import MathJaxPagedownWidget, PagedownWidget

try:
    from django_select2.widgets import HeavySelect2MultipleWidget, Select2Widget
except ImportError:
    HeavySelect2MultipleWidget = None
    Select2Widget = None

use_select2 = HeavySelect2MultipleWidget is not None and 'django_select2' in settings.INSTALLED_APPS


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['name', 'about', 'organizations', 'timezone', 'language', 'ace_theme']
        widgets = {'name': TextInput(attrs={'style': 'width: 100%; box-sizing: border-box'})}
        if Select2Widget is not None:
            widgets['timezone'] = Select2Widget(attrs={'style': 'width: 200px'})
            widgets['language'] = Select2Widget(attrs={'style': 'width: 300px'})
            widgets['ace_theme'] = Select2Widget(attrs={'style': 'width: 300px'})

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ProfileForm, self).__init__(*args, **kwargs)
        if not user.has_perm('judge.edit_all_organization'):
            self.fields['organizations'].queryset = Organization.objects.filter(
                Q(is_open=True) | Q(id__in=user.profile.organizations.all())
            )

    def clean_name(self):
        return fix_unicode(self.cleaned_data['name'])


class ProblemSubmitForm(ModelForm):
    source = CharField(max_length=65536, widget=AceWidget(theme='twilight'))

    def __init__(self, *args, **kwargs):
        super(ProblemSubmitForm, self).__init__(*args, **kwargs)
        self.fields['problem'].empty_label = None
        self.fields['problem'].widget = forms.HiddenInput()
        self.fields['language'].empty_label = None
        self.fields['language'].label_from_instance = attrgetter('display_name')
        self.fields['language'].queryset = Language.objects.filter(judges__online=True).distinct()

    class Meta:
        model = Submission
        fields = ['problem', 'source', 'language']


class EditOrganizationForm(ModelForm):
    class Meta:
        model = Organization
        fields = ['about']


class NewMessageForm(ModelForm):
    class Meta:
        model = PrivateMessage
        fields = ['title', 'content']
        widgets = {}
        if PagedownWidget is not None:
            widgets['content'] = MathJaxPagedownWidget()


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


class ProblemAddForm(ProblemEditForm):
    class Meta(ProblemEditForm.Meta):
        fields = ['code'] + ProblemEditForm.Meta.fields


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(CustomAuthenticationForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Username'})
        self.fields['password'].widget.attrs.update({'placeholder': 'Password'})
