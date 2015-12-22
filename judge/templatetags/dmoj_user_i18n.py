from django import template

from judge.user_translations import ugettext

register = template.Library()


@register.filter(name='user_trans')
def do_user_trans(text):
    return ugettext(text)
