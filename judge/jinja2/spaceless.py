import re

from jinja2 import nodes
from jinja2.ext import Extension
from markupsafe import Markup


class SpacelessExtension(Extension):
    """
    Removes whitespace between HTML tags at compile time, including tab and newline characters.
    It does not remove whitespace between jinja2 tags or variables. Neither does it remove whitespace between tags
    and their text content.
    Adapted from coffin:
        https://github.com/coffin/coffin/blob/master/coffin/template/defaulttags.py
    Adapted from StackOverflow:
        https://stackoverflow.com/a/23741298/1090657
    """

    tags = {'spaceless'}

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(['name:endspaceless'], drop_needle=True)
        return nodes.CallBlock(
            self.call_method('_strip_spaces', [], [], None, None),
            [], [], body,
        ).set_lineno(lineno)

    def _strip_spaces(self, caller=None):
        return Markup(re.sub(r'>\s+<', '><', caller().unescape().strip()))
