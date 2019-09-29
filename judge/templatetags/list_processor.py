from operator import attrgetter, itemgetter

from django import template

register = template.Library()


@register.filter(name='list_attr')
def list_attr(iterable, prop):
    result = []
    for item in iterable:
        if hasattr(item, str(prop)):
            result.append(getattr(item, prop))
        else:
            try:
                result.append(item[prop])
            except KeyError:
                result.append('')
            except TypeError:
                try:
                    result.append(item[int(prop)])
                except (IndexError, ValueError, TypeError):
                    result.append('')
    return result


@register.filter(name='list_getitem')
def list_getitem(iterable, prop):
    return list(map(itemgetter(prop), iterable))


@register.filter(name='list_getindex')
def list_getindex(iterable, index):
    return list(map(itemgetter(int(index)), iterable))


@register.filter(name='list_getattr')
def list_getattr(iterable, prop):
    return list(map(attrgetter(prop), iterable))


@register.filter(name='sum_list')
def sum_list(iterable):
    return sum(iterable)


@register.filter(name='max_list')
def max_list(iterable):
    if not iterable:
        return 0
    return max(iterable)


@register.filter(name='min_list')
def min_list(iterable):
    if not iterable:
        return 0
    return min(iterable)
