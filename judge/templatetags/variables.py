import re

from django import template

register = template.Library()


class SetVarNode(template.Node):
    def __init__(self, new_val, var_name):
        self.new_val = template.Variable(new_val)
        self.var_name = var_name

    def render(self, context):
        context[self.var_name] = self.new_val.resolve(context)
        return ''


@register.tag
def setvar(parser, token):
    # This version uses a regular expression to parse tag contents.
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]
    m = re.search(r'(.*?) as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%r tag had invalid arguments" % tag_name
    return SetVarNode(*m.groups())
