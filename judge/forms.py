from operator import attrgetter

import pyotp
from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.forms import ModelForm, CharField, TextInput, Form
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from django_ace import AceWidget
from judge.models import Organization, Profile, Submission, PrivateMessage, Language
from judge.utils.subscription import newsletter_id
from judge.widgets import MathJaxPagedownWidget, HeavyPreviewPageDownWidget, PagedownWidget, \
    Select2Widget, Select2MultipleWidget


def fix_unicode(string, unsafe=tuple(u'\u202a\u202b\u202d\u202e')):
    return string + (sum(k in unsafe for k in string) - string.count(u'\u202c')) * u'\u202c'


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['language', 'ace_theme', 'user_script']
        widgets = {
            'user_script': AceWidget(theme='github'),
            'language': Select2Widget(attrs={'style': 'width:200px'}),
            'ace_theme': Select2Widget(attrs={'style': 'width:200px'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ProfileForm, self).__init__(*args, **kwargs)


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
        if HeavyPreviewPageDownWidget is not None:
            widgets['about'] = HeavyPreviewPageDownWidget(preview=reverse_lazy('organization_preview'))


class NewMessageForm(ModelForm):
    class Meta:
        model = PrivateMessage
        fields = ['title', 'content']
        widgets = {}
        if PagedownWidget is not None:
            widgets['content'] = MathJaxPagedownWidget()


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(CustomAuthenticationForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': _('Username')})
        self.fields['password'].widget.attrs.update({'placeholder': _('Password')})

        self.has_google_auth = self._has_social_auth('GOOGLE_OAUTH2')
        self.has_facebook_auth = self._has_social_auth('FACEBOOK')
        self.has_github_auth = self._has_social_auth('GITHUB_SECURE')
        self.has_dropbox_auth = self._has_social_auth('DROPBOX_OAUTH2')

    def _has_social_auth(self, key):
        return (getattr(settings, 'SOCIAL_AUTH_%s_KEY' % key, None) and
                getattr(settings, 'SOCIAL_AUTH_%s_SECRET' % key, None))


class NoAutoCompleteCharField(forms.CharField):
    def widget_attrs(self, widget):
        attrs = super(NoAutoCompleteCharField, self).widget_attrs(widget)
        attrs['autocomplete'] = 'off'
        return attrs


class TOTPForm(Form):
    TOLERANCE = getattr(settings, 'DMOJ_TOTP_TOLERANCE_HALF_MINUTES', 1)

    totp_token = NoAutoCompleteCharField(validators=[
        RegexValidator('^[0-9]{6}$', _('Two Factor Authentication tokens must be 6 decimal digits.'))
    ])

    def __init__(self, *args, **kwargs):
        self.totp_key = kwargs.pop('totp_key')
        super(TOTPForm, self).__init__(*args, **kwargs)

    def clean_totp_token(self):
        if not pyotp.TOTP(self.totp_key).verify(self.cleaned_data['totp_token'], valid_window=self.TOLERANCE):
            raise ValidationError(_('Invalid Two Factor Authentication token.'))
