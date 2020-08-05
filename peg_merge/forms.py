from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.forms import BooleanField, CharField, Form
from django.utils.translation import gettext as _

from judge.models import Profile
from judge.utils.recaptcha import ReCaptchaField, ReCaptchaWidget


class WCIPEGMergeRequestForm(Form):
    handle = CharField(max_length=50, validators=[UnicodeUsernameValidator()])

    if ReCaptchaField is not None:
        captcha = ReCaptchaField(widget=ReCaptchaWidget())

    def clean_handle(self):
        try:
            profile = Profile.objects.get(user__username=self.cleaned_data['handle'], user__is_active=True)
        except Profile.DoesNotExist:
            raise ValidationError(_("Account doesn't exist."))
        else:
            if profile.is_peg:
                raise ValidationError(_('Account must be a DMOJ account.'))
        return self.cleaned_data['handle']

    def send_email(self, url, email):
        EmailMessage(
            subject=_('WCIPEG Account Merge Request'),
            body=_('To authenticate the merge, please use the link below:\n\n%s\n\n') % url +
            _('You may then login to your native DMOJ account.\n\n') +
            _('If you did not request this merge, you can safely ignore this email.'),
            to=[email],
        ).send()


class WCIPEGMergeActivationForm(Form):
    accept = BooleanField(label=_('I understand and would still like to merge my accounts:'))
