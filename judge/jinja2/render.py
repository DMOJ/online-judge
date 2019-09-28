from django.template import (Context, Template as DjangoTemplate, TemplateSyntaxError as DjangoTemplateSyntaxError,
                             VariableDoesNotExist)

from . import registry

MAX_CACHE = 100
django_cache = {}


def compile_template(code):
    if code in django_cache:
        return django_cache[code]

    # If this works for re.compile, it works for us too.
    if len(django_cache) > MAX_CACHE:
        django_cache.clear()

    t = django_cache[code] = DjangoTemplate(code)
    return t


@registry.function
def render_django(template, **context):
    try:
        return compile_template(template).render(Context(context))
    except (VariableDoesNotExist, DjangoTemplateSyntaxError):
        return 'Error rendering: %r' % template
