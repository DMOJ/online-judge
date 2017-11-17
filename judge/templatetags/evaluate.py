from django import template

register = template.Library()
template_cache = {}

MAX_CACHE = 100


def compile_template(template_code):
    if template_code in template_cache:
        return template_cache[template_code]

    # If this works for re.compile, it works for us too.
    if len(template_cache) > MAX_CACHE:
        template_cache.clear()

    t = template_cache[template_code] = template.Template(template_code)
    return t


@register.simple_tag(name='evaluate', takes_context=True)
def evaluate_tag(context, template_code):
    try:
        return compile_template(template_code).render(context)
    except (template.VariableDoesNotExist, template.TemplateSyntaxError):
        return 'Error rendering: %r' % template_code
