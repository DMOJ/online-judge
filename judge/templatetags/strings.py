from django import template
from django.template import Node, NodeList, Variable, VariableDoesNotExist

register = template.Library()


@register.filter(name='split')
def split(value, arg):
    return value.split('\n')


def do_startswith(parser, token, negate):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, string, start_string = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires two arguments" % token.contents.split()[0]
    if not (start_string[0] == start_string[-1] and start_string[0] in ('"', "'")):
        raise template.TemplateSyntaxError, "%r start strings argument should be in quotes" % tag_name

    end_tag = 'end' + tag_name
    nodelist_true = parser.parse(('else', end_tag))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse((end_tag,))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()
    return IfStartsWithNode(string, start_string, nodelist_true, nodelist_false, negate)


class IfStartsWithNode(Node):
    def __init__(self, string, start_string, nodelist_true, nodelist_false, negate):
        self.start_string, self.string = Variable(start_string), Variable(string)
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.negate = negate
        self.negate = negate

    def __repr__(self):
        return "<IfStartsWithNode>"

    def render(self, context):
        string = self.string.resolve(context)
        start_string = self.start_string.resolve(context)

        if (self.negate and not string.startswith(start_string)) or (
            not self.negate and string.startswith(start_string)):
            return self.nodelist_true.render(context)
        return self.nodelist_false.render(context)


@register.tag
def ifstartswith(parser, token):
    return do_startswith(parser, token, False)


@register.tag
def ifnotstartswith(parser, token):
    return do_startswith(parser, token, True)
