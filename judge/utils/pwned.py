"""
Based on https://github.com/ubernostrum/pwned-passwords-django.

Original license:

Copyright (c) 2018, James Bennett
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above
      copyright notice, this list of conditions and the following
      disclaimer in the documentation and/or other materials provided
      with the distribution.
    * Neither the name of the author nor the names of other
      contributors may be used to endorse or promote products derived
      from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."""


import hashlib
import logging

import requests
from django.conf import settings
from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from judge.utils.unicode import utf8bytes

log = logging.getLogger(__name__)

API_ENDPOINT = 'https://api.pwnedpasswords.com/range/{}'
REQUEST_TIMEOUT = 2.0  # 2 seconds


def _get_pwned(prefix):
    """
    Fetches a dict of all hash suffixes from Pwned Passwords for a
    given SHA-1 prefix.
    """
    try:
        response = requests.get(
            url=API_ENDPOINT.format(prefix),
            timeout=getattr(
                settings,
                'PWNED_PASSWORDS_API_TIMEOUT',
                REQUEST_TIMEOUT,
            ),
        )
        response.raise_for_status()
    except requests.RequestException:
        # Gracefully handle timeouts and HTTP error response codes.
        log.warning('Skipped Pwned Passwords check due to error', exc_info=True)
        return None

    results = {}
    for line in response.text.splitlines():
        line_suffix, _, times = line.partition(':')
        results[line_suffix] = int(times.replace(',', ''))

    return results


def pwned_password(password):
    """
    Checks a password against the Pwned Passwords database.
    """
    if not isinstance(password, str):
        raise TypeError('Password values to check must be strings.')
    password_hash = hashlib.sha1(utf8bytes(password)).hexdigest().upper()
    prefix, suffix = password_hash[:5], password_hash[5:]
    results = _get_pwned(prefix)
    if results is None:
        # Gracefully handle timeouts and HTTP error response codes.
        return None
    return results.get(suffix, 0)


class PwnedPasswordsValidator(object):
    """
    Password validator which checks the Pwned Passwords database.
    """

    def validate(self, password, user=None):
        amount = pwned_password(password)
        if amount is None:
            # HIBP API failure. Instead of allowing a potentially compromised
            # password, check Django's list of common passwords generated from
            # the same database.
            CommonPasswordValidator().validate(password, user)
        elif amount:
            raise ValidationError(_('This password is too common.'))

    def get_help_text(self):
        return _("Your password can't be a commonly used password.")
