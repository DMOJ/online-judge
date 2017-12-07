import hashlib

from django.contrib.auth.models import AbstractUser
from django.utils.http import urlencode

from judge.models import Profile
from . import registry


@registry.function
def gravatar(email, size=80, default=None):
    if isinstance(email, Profile):
        if default is None:
            default = email.mute
        email = email.user.email
    elif isinstance(email, AbstractUser):
        email = email.email

    gravatar_url = '//www.gravatar.com/avatar/' + hashlib.md5(email.strip().lower()).hexdigest() + '?'
    args = {'d': 'identicon', 's': str(size)}
    if default:
        args['f'] = 'y'
    gravatar_url += urlencode(args)
    return gravatar_url
