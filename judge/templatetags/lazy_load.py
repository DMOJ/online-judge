from copy import deepcopy

from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static
from lxml import html

from judge import lxml_tree

blank = static('blank.gif')

register = template.Library()


@register.filter(is_safe=True)
def lazy_load(text):
    tree = lxml_tree.fromstring(text)
    for img in tree.xpath('.//img'):
        noscript = html.Element('noscript')
        noscript.append(deepcopy(img))
        img.addprevious(noscript)
        img.set('data-src', img.get('src'))
        img.set('src', blank)
    return tree
