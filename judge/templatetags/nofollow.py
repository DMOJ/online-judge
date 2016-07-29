from urlparse import urlparse

from django import template
from django.conf import settings

from judge import lxml_tree

register = template.Library()
whitelist = getattr(settings, 'NOFOLLOW_EXCLUDED', set())


@register.filter(is_safe=True, name='nofollowexternal')
def no_follow_external_links(text):
    tree = lxml_tree.fromstring(text)
    for anchor in tree.xpath('.//a'):
        href = anchor.get('href')
        if href:
            url = urlparse(href)
            if url.netloc and url.netloc not in whitelist:
                anchor.set('rel', 'nofollow')
    return tree
