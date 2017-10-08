from django import template

register = template.Library()


@register.simple_tag(name='evaluate', takes_context=True)
def evaluate_tag(context, template_code):
    try:
        t = template.Template(template_code)
        return t.render(context)
    except (template.VariableDoesNotExist, template.TemplateSyntaxError):
        return 'Error rendering: %r' % template_code
