import re
from collections import defaultdict

from django import template
from django.core.urlresolvers import reverse
from lxml.html import Element

from judge import lxml_tree
from judge.models import Profile

register = template.Library()

rereference = re.compile(r'\[(user):(\w+)\]')


def get_user(username, rank):
    if rank is None:
        element = Element('span')
    else:
        element = Element('a', {'class': rank, 'href': reverse('user_page', args=[username])})
    element.text = username
    return element


def get_user_info(usernames):
    return dict(Profile.objects.filter(user__username__in=usernames).values_list('user__username', 'display_rank'))


reference_map = {
    'user': (get_user, get_user_info),
}


def process_reference(text):
    # text/tail -> text/tail + elements
    last = 0
    tail = text
    prev = None
    elements = []
    for piece in rereference.finditer(text):
        if prev is None:
            tail = text[last:piece.start()]
        else:
            prev.append(text[last:piece.start()])
        prev = list(piece.groups())
        elements.append(prev)
        last = piece.end()
    if prev is not None:
        prev.append(text[last:])
    return tail, elements


def populate_list(queries, list, element, tail, children):
    if children:
        for elem in children:
            queries[elem[0]].append(elem[1])
        list.append((element, tail, children))


def update_tree(list, results, is_tail=False):
    for element, text, children in list:
        after = []
        for type, name, tail in children:
            child = reference_map[type][0](name, results[type].get(name))
            child.tail = tail
            after.append(child)

        after = iter(reversed(after))
        if is_tail:
            element.tail = text
            link = element.getnext()
            if link is None:
                link = next(after)
                element.getparent().append(link)
        else:
            element.text = text
            link = next(after)
            element.insert(0, link)
        for child in after:
            link.addprevious(child)
            link = child


@register.filter(is_safe=True)
def reference(text):
    tree = lxml_tree.fromstring(text)
    texts = []
    tails = []
    queries = defaultdict(list)
    for element in tree.iter():
        if element.text:
            populate_list(queries, texts, element, *process_reference(element.text))
        if element.tail:
            populate_list(queries, tails, element, *process_reference(element.tail))

    results = {type: reference_map[type][1](values) for type, values in queries.iteritems()}
    update_tree(texts, results, is_tail=False)
    update_tree(tails, results, is_tail=True)
    return tree
