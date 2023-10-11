import re
from typing import Any, Dict, List, Optional, Pattern

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.forms import ValidationError
from django.template import loader
from django.utils.translation import gettext


bad_mail_regex: List[Pattern[str]] = list(map(re.compile, settings.BAD_MAIL_PROVIDER_REGEX))


def validate_email_domain(email: str) -> None:
    if '@' in email:
        domain = email.split('@')[-1].lower()
        if domain in settings.BAD_MAIL_PROVIDERS or any(regex.match(domain) for regex in bad_mail_regex):
            raise ValidationError(gettext('Your email provider is not allowed due to history of abuse. '
                                          'Please use a reputable email provider.'))


# Inspired by django.contrib.auth.forms.PasswordResetForm.send_mail
def send_mail(
    context: Dict[str, Any],
    *,
    from_email: Optional[str] = None,
    to_email: str,
    subject_template_name: str,
    email_template_name: str,
    html_email_template_name: Optional[str] = None,
) -> None:
    subject = loader.render_to_string(subject_template_name, context)
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    body = loader.render_to_string(email_template_name, context)

    email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
    if html_email_template_name is not None:
        html_email = loader.render_to_string(html_email_template_name, context)
        email_message.attach_alternative(html_email, 'text/html')

    email_message.send()
