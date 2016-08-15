from django import template
from lxml import html

from judge import lxml_tree
from judge.utils.texoid import get_result

register = template.Library()


@register.filter(is_safe=True)
def latex_math(text):
    tree = lxml_tree.fromstring(text)
    for latex in tree.xpath('.//latex'):

        result = get_result(latex.text)
        if result:
            img = html.Element('img')
            img.set('src', result['svg'])
            img.set('onerror', "this.src='%s'" % result['png'])
        else:
            img = html.Element('em')
            img.text = 'Texoid rendering error, check logs.'
        latex.getParent().replace(latex, img)
    return tree
