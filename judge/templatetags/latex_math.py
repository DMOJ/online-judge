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
            tag = html.Element('pre')
            tag.text = 'LaTeX rendering error\n' + latex.text
        elif 'error' not in result:
            img = html.Element('img')
            img.set('src', result['svg'])
            img.set('onerror', "this.src='%s';this.onerror=null" % result['png'])

            ident = result['meta']
            img.set('width', ident['width'])
            img.set('height', ident['height'])
            style = []
            if 'inline' not in latex.attrib:
                tag = html.Element('div')
                style += ['text-align: center']
            else:
                tag = html.Element('span')
            style += ['max-width: 100%', 'height: %s' % ident['height'],
                      'max-height: %s' % ident['height'], 'width: %s' % ident['height']]
            tag.set('style', ';'.join(style))
            tag.append(img)
        else:
            tag = html.Element('pre')
            tag.text = result['error']
        latex.getparent().replace(latex, tag)
    return tree
