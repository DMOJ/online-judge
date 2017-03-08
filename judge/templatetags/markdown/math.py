import re

import mistune

from judge.utils.mathoid import MathoidMathParser


class MathInlineGrammar(mistune.InlineGrammar):
    block_math = re.compile(r'^\$\$(.*?)\$\$|^\\\[(.*?)\\\]', re.DOTALL)
    math = re.compile(r'^~(.*?)~|^\\\((.*?)\\\)', re.DOTALL)


class MathInlineLexer(mistune.InlineLexer):
    default_rules = ['block_math', 'math'] + mistune.InlineLexer.default_rules
    grammar_class = MathInlineGrammar

    def output_block_math(self, m):
        return self.renderer.block_math(m.group(1) or m.group(2))

    def output_math(self, m):
        return self.renderer.math(m.group(1) or m.group(2))


class MathRenderer(mistune.Renderer):
    def __init__(self, *args, **kwargs):
        if kwargs.pop('math', False):
            self.mathoid = MathoidMathParser(kwargs.pop('math_engine', None) or 'svg')
        else:
            self.mathoid = None
        super(MathRenderer, self).__init__(*args, **kwargs)

    def block_math(self, math):
        if self.mathoid is None:
            return r'\[%s\]' % math
        return self.mathoid.display_math(math)

    def math(self, math):
        if self.mathoid is None:
            return r'\(%s\)' % math
        return self.mathoid.inline_math(math)
