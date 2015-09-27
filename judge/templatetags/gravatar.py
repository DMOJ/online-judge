### gravatar.py ###############
### place inside a 'templatetags' directory inside the top level of a Django app (not project, must be inside an app)
### at the top of your page template include this:
### {% load gravatar %}
### and to use the url do this:
### <img src="{% gravatar_url 'someone@somewhere.com' %}">
### or
### <img src="{% gravatar_url sometemplatevariable %}">
### just make sure to update the "default" image path below
 
from django import template
import urllib, hashlib
 
register = template.Library()


class GravatarUrlNode(template.Node):
    def __init__(self, email, size='80', default=False, as_=None, variable=None):
        self.email = template.Variable(email)
        self.size = template.Variable(size)
        self.default = template.Variable(default)
        self.variable = as_ and variable
 
    def render(self, context):
        try:
            email = self.email.resolve(context)
        except template.VariableDoesNotExist:
            return ''
        try:
            size = self.size.resolve(context)
        except template.VariableDoesNotExist:
            size = 80
        try:
            default = self.default.resolve(context)
        except template.VariableDoesNotExist:
            default = False

        gravatar_url = '//www.gravatar.com/avatar/' + hashlib.md5(email.strip().lower()).hexdigest() + '?'
        args = {'d': 'identicon', 's': str(size)}
        if default:
            args['f'] = 'y'
        gravatar_url += urllib.urlencode(args)

        if self.variable is not None:
            context[self.variable] = gravatar_url
            return ''
        return gravatar_url
 
@register.tag
def gravatar_url(parser, token):
    try:
        return GravatarUrlNode(*token.split_contents()[1:])
    except ValueError:
        raise template.TemplateSyntaxError, '%r tag requires an email and an optional size' % token.contents.split()[0]
