import urllib
from urlparse import urljoin

from django import template

from judge import lxml_tree

register = template.Library()


@register.filter(is_safe=True, name='absolutify')
def absolute_links(text, url):
    tree = lxml_tree.fromstring(text)
    for anchor in tree.xpath('.//a'):
        href = anchor.get('href')
        if href:
            anchor.set('href', urljoin(url, href))
    return tree


@register.filter(name='urljoin')
def join(first, second):
    return urljoin(first, second)
