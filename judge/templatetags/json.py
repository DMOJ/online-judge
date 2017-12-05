from __future__ import absolute_import

import json

from django import template

register = template.Library()


@register.filter(name='json')
def to_json(data):
    return json.dumps(data)
