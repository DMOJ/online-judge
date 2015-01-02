from django import template
from itertools import count

register = template.Library()


class GetCounterNode(template.Node):
    def __init__(self, var_name, start=1):
        self.var_name = var_name
        self.start = start

    def render(self, context):
        context[self.var_name] = count(self.start).next
        return ''


@register.tag
def get_counter(parser, token):
    try:
        return GetCounterNode(*token.contents.split()[1:])
    except ValueError:
        raise template.TemplateSyntaxError, '%r tag requires arguments' % token.contents.split()[0]
