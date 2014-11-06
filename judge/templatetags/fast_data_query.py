from django import template
from django.core.cache import cache
from judge.models import Language

register = template.Library()


class LanguageShortDisplayNode(template.Node):
    def __init__(self, language):
        self.language_id = template.Variable(language)
 
    def render(self, context):
        id = int(self.language_id.resolve(context))
        key = 'lang_sdn:%d' % id
        result = cache.get(key)
        if result is not None:
            return result
        result = Language.objects.get(id=id).short_display_name
        cache.set(key, result, 86400)
        return result
 
@register.tag
def language_short_display(parser, token):
    try:
        return LanguageShortDisplayNode(token.split_contents()[1])
    except IndexError:
        raise template.TemplateSyntaxError('%r tag requires language id' % token.contents.split()[0])
