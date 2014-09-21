from django import template
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
import markdown_trois
from django.conf import settings
from markdown_trois.conf.settings import MARKDOWN_TROIS_HELP_URL

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(value, style="default"):
    """Processes the given value as Markdown, optionally using a particular
    Markdown style/config

    Syntax::

        {{ value|markdown }}            {# uses the "default" style #}
        {{ value|markdown:"mystyle" }}

    Markdown "styles" are defined by the `MARKDOWN_TROIS_STYLES` setting.
    """
    try:
        return mark_safe(markdown_trois.markdown(value, style))
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError("Error in `markdown` filter: "
                                               "The python-markdown2 library isn't installed.")
        return force_unicode(value)


markdown_filter.is_safe = True


@register.tag(name="markdown")
def markdown_tag(parser, token):
    nodelist = parser.parse(('endmarkdown',))
    bits = token.split_contents()
    if len(bits) == 1:
        style = "default"
    elif len(bits) == 2:
        style = bits[1]
    else:
        raise template.TemplateSyntaxError("`markdown` tag requires exactly "
                                           "zero or one arguments")
    parser.delete_first_token()  # consume '{% endmarkdown %}'
    return MarkdownNode(style, nodelist)


class MarkdownNode(template.Node):
    def __init__(self, style, nodelist):
        self.style = style
        self.nodelist = nodelist

    def render(self, context):
        value = self.nodelist.render(context)
        try:
            return mark_safe(markdown_trois.markdown(value, self.style))
        except ImportError:
            if settings.DEBUG:
                raise template.TemplateSyntaxError("Error in `markdown` tag: "
                                                   "The python-markdown2 library isn't installed.")
            return force_unicode(value)


@register.inclusion_tag("markdown_trois/markdown_cheatsheet.html")
def markdown_cheatsheet():
    return {"help_url": getattr(settings, 'MARKDOWN_TROIS_HELP_URL', MARKDOWN_TROIS_HELP_URL)}


@register.simple_tag
def markdown_allowed():
    return ('<a href="%s" target="_blank">Markdown syntax</a> allowed, but no raw HTML. '
            'Examples: **bold**, *italic*, indent 4 spaces for a code block.'
            % getattr(settings, 'MARKDOWN_TROIS_HELP_URL', MARKDOWN_TROIS_HELP_URL))