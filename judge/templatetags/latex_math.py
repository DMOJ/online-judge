from django import template
from lxml import html

from judge import lxml_tree
from judge.utils.texoid import get_result

register = template.Library()


@register.filter(is_safe=True)
def latex_math(text):
    tree = lxml_tree.fromstring(text)
    for latex in tree.xpath('.//latex'):
        img = html.Element('img')
        result = get_result(latex.text)
        img.set('src', result['svg'])
        img.set('onerror', "this.src='%s'" % result['png'])
        latex.getParent().replace(latex, img)
    return tree
