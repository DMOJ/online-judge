import re

import mistune

from judge.utils.mathoid import MathoidMathParser


class MathBlockLexer(mistune.BlockLexer):
    def __init__(self, *args, **kwargs):
        self.rules.block_math = re.compile(r'\$\$(.*?)\$\$|\\\[(.*?)\\\]', re.DOTALL)
        self.default_rules.extend(['block_math'])
        super(MathBlockLexer, self).__init__(*args, **kwargs)

    def parse_block_math(self, m):
        self.tokens.append({
            'type': 'block_math',
            'text': m.group(1) or m.group(2)
        })


class MathInlineLexer(mistune.InlineLexer):
    def __init__(self, *args, **kwargs):
        self.rules.math = re.compile(r'~(.*?)~|\\\((.*?)\\\)', re.S)
        self.default_rules.insert(0, 'math')
        super(MathInlineLexer, self).__init__(*args, **kwargs)

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
