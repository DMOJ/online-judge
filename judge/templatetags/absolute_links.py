from django import template

from judge import lxml_tree

register = template.Library()


@register.filter(is_safe=True, name='absolutify')
def absolute_links(text, make_absolute):
    tree = lxml_tree.fromstring(text)
    for anchor in tree.xpath('.//a'):
        href = anchor.get('href')
        if href:
            anchor.set('href', make_absolute(href))
    return tree
