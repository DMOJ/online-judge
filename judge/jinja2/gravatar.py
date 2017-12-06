import hashlib

from django.utils.http import urlencode

from . import registry


@registry.function
def gravatar(email, size=80, default=None):
    email = getattr(email, 'email', email)
    gravatar_url = '//www.gravatar.com/avatar/' + hashlib.md5(email.strip().lower()).hexdigest() + '?'
    args = {'d': 'identicon', 's': str(size)}
    if default:
        args['f'] = 'y'
    gravatar_url += urlencode(args)
    return gravatar_url
