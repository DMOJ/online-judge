import re
from collections import defaultdict

from django import template
from django.core.urlresolvers import reverse
from lxml.html import Element

from judge import lxml_tree
from judge.models import Contest
from judge.models import Problem
from judge.models import Profile
from judge.ratings import rating_class, rating_progress

register = template.Library()

rereference = re.compile(r'\[(r?user):(\w+)\]')


def get_user(username, rank):
    if rank is None:
        element = Element('span')
    else:
        element = Element('a', {'class': rank, 'href': reverse('user_page', args=[username])})
    element.text = username
    return element


def get_user_info(usernames):
    return dict(Profile.objects.filter(user__username__in=usernames).values_list('user__username', 'display_rank'))


def get_user_rating(username, rating):
    element = Element('a', {'class': 'rate-group', 'href': reverse('user_page', args=[username])})
    if rating:
        rating_css = rating_class(rating)
        rate_box = Element('span', {'class': 'rate-box ' + rating_css})
        rate_box.append(Element('span', {'style': 'height: %3.fem' % rating_progress(rating)}))
        user = Element('span', {'class': 'rating ' + rating_css})
        user.text = username
        element.append(rate_box)
        element.append(user)
    else:
        element.text = username
    return element


def get_user_rating_info(usernames):
    return dict(Profile.objects.filter(user__username__in=usernames).values_list('user__username', 'rating'))


reference_map = {
    'user': (get_user, get_user_info),
    'ruser': (get_user_rating, get_user_rating_info),
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


@register.filter(name='item_title')
def item_title(item):
    if isinstance(item, Problem):
        return item.name
    elif isinstance(item, Contest):
        return item.name
    return '<Unknown>'
