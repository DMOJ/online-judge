from django import template
from lxml import html

from judge import lxml_tree
from judge.utils.texoid import TexoidRenderer, TEXOID_ENABLED

register = template.Library()


@register.filter(is_safe=True)
def latex_math(text):
    if not TEXOID_ENABLED:
        return text

    tree = lxml_tree.fromstring(text)
    texoid = TexoidRenderer()

    for latex in tree.xpath('.//latex'):
        result = texoid.get_result(latex.text)
        if not result:
            img = html.Element('pre')
            img.text = 'LaTeX rendering error\n' + latex.text
        elif 'error' not in result:
            img = html.Element('img')
            img.set('src', result['svg'])
            img.set('onerror', "this.src='%s';this.onerror=null" % result['png'])
            if 'inline' not in latex.attrib:
                tag = html.Element('div')
                tag.set('style', 'text-align: center')
                tag.append(img)
                img = tag
        else:
            img = html.Element('pre')
            img.text = result['error']
        latex.getparent().replace(latex, img)
    return tree
