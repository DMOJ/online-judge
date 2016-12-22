from operator import attrgetter

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.forms import ModelForm, CharField, TextInput
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from django_ace import AceWidget
from judge.models import Organization, Profile, Submission, Problem, PrivateMessage, Language
from judge.utils.subscription import newsletter_id
from judge.widgets import MathJaxPagedownWidget, HeavyPreviewPageDownWidget, PagedownWidget, \
    Select2Widget, Select2MultipleWidget


def fix_unicode(string, unsafe=tuple(u'\u202a\u202b\u202d\u202e')):
    return string + (sum(k in unsafe for k in string) - string.count(u'\u202c')) * u'\u202c'


class ProfileForm(ModelForm):
    if newsletter_id is not None:
        newsletter = forms.BooleanField(label=_('Subscribe to newsletter?'), initial=False, required=False)

    class Meta:
        model = Profile
        fields = ['name', 'about', 'organizations', 'timezone', 'language', 'ace_theme', 'user_script', 'math_engine']
        widgets = {
            'name': TextInput(attrs={'style': 'width:100%;box-sizing:border-box'}),
            'user_script': AceWidget(theme='github'),
            'timezone': Select2Widget(attrs={'style': 'width:200px'}),
            'language': Select2Widget(attrs={'style': 'width:200px'}),
            'ace_theme': Select2Widget(attrs={'style': 'width:200px'}),
            'math_engine': Select2Widget(attrs={'style': 'width:200px'})
        }

        if HeavyPreviewPageDownWidget is not None:
            widgets['about'] = HeavyPreviewPageDownWidget(
                preview=reverse_lazy('profile_preview'),
                attrs={'style': 'max-width:700px;min-width:700px;width:700px'}
            )

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
    source = CharField(max_length=65536, widget=AceWidget(theme='twilight', no_ace_media=True))

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
        fields = ['about', 'admins']
        widgets = {'admins': Select2MultipleWidget()}
        if PagedownWidget is not None:
            widgets['about'] = MathJaxPagedownWidget()


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

        self.has_google_auth = self._has_social_auth('GOOGLE_OAUTH2')
        self.has_facebook_auth = self._has_social_auth('FACEBOOK')
        self.has_github_auth = self._has_social_auth('GITHUB_SECURE')
        self.has_dropbox_auth = self._has_social_auth('DROPBOX_OAUTH2')

    def _has_social_auth(self, key):
        return (getattr(settings, 'SOCIAL_AUTH_%s_KEY' % key, None) and
                getattr(settings, 'SOCIAL_AUTH_%s_SECRET' % key, None))
