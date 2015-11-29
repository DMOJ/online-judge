import re

from django import template
from django.core.cache import cache

register = template.Library()


class CacheVersionNode(template.Node):
    def __init__(self, var_name, *key):
        self.key = map(template.Variable, key)
        self.var_name = var_name

    def render(self, context):
        key = 'version:' + '-'.join(str(key.resolve(context)) for key in self.key)
        cache.add(key, 0, None)
        context[self.var_name] = cache.get(key)
        return ''


@register.tag(name='get_cache_version')
def get_cache_version(parser, token):
    # This version uses a regular expression to parse tag contents.
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]
    m = re.search(r'(.*?) as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%r tag had invalid arguments" % tag_name
    return CacheVersionNode(m.group(2), *m.group(1).split())
