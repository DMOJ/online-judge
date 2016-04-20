from django import template

register = template.Library()


@register.filter(name='split')
def split(value):
    return value.split('\n')


@register.filter(name='cutoff')
def cutoff(value, length):
    return value[:int(length)]
