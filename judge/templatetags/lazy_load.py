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
        src = img.get('src')
        if src.startswith('data'):
            continue
        noscript = html.Element('noscript')
        noscript.append(deepcopy(img))
        img.addprevious(noscript)
        img.set('data-src', src)
        img.set('src', blank)
        img.set('class', img.get('class') + ' unveil' if img.get('class') else 'unveil')
    return tree
