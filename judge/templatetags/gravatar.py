import hashlib
import urllib

from django import template

register = template.Library()


def get_gravatar_url(email, size=80, default=None):
    gravatar_url = '//www.gravatar.com/avatar/' + hashlib.md5(email.strip().lower()).hexdigest() + '?'
    args = {'d': 'identicon', 's': str(size)}
    if default:
        args['f'] = 'y'
    gravatar_url += urllib.urlencode(args)
    return gravatar_url


@register.simple_tag
def gravatar_url(email, size=80, default=None):
    return get_gravatar_url(email, size, default)
