#!/usr/bin/env python
# Copyright (c) 2008-2010 ActiveState Corp.
# License: MIT (http://www.opensource.org/licenses/mit-license.php)

r"""A small Django app that provides template tags for Markdown using the
python-markdown2 library.

Based off <http://github.com/trentm/django-markdown-deux>.
"""
from django.conf import settings
from markdown_trois.conf.settings import MARKDOWN_TROIS_DEFAULT_STYLE

__version_info__ = (1, 0, 4)
__version__ = '.'.join(map(str, __version_info__))
__author__ = "Trent Mick"

import markdown2


def markdown(text, style="default"):
    if not text:
        return ""
    return markdown2.markdown(text, **get_style(style))


def get_style(style):
    styles = getattr(settings, 'MARKDOWN_TROIS_STYLES', {})
    try:
        return styles[style]
    except KeyError:
        return styles.get("default", MARKDOWN_TROIS_DEFAULT_STYLE)
