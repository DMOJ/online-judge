from copy import deepcopy

from django.templatetags.static import static
from lxml import html


def lazy_load(tree):
    blank = static('blank.gif')
    for img in tree.xpath('.//img'):
        src = img.get('src', '')
        if src.startswith('data') or '-math' in img.get('class', ''):
            continue
        noscript = html.Element('noscript')
        copy = deepcopy(img)
        copy.tail = ''
        noscript.append(copy)
        img.addprevious(noscript)
        img.set('data-src', src)
        img.set('src', blank)
        img.set('class', img.get('class') + ' unveil' if img.get('class') else 'unveil')
