from django.template import Node, Library, Variable, FilterExpression, TemplateSyntaxError
import math
import re

register = Library()

# taken from http://lybniz2.sourceforge.net/safeeval.html
# make a list of safe functions
math_safe_list = ['acos', 'asin', 'atan', 'atan2', 'ceil', 'cos', 'cosh', 'degrees', 'e', 'exp', 'fabs', 'floor', 'fmod', 'frexp', 'hypot', 'ldexp', 'log', 'log10', 'modf', 'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh']

# use the list to filter the local namespace
math_safe_dict = dict([(k, getattr(math, k)) for k in math_safe_list])

# add any needed builtins back in.
for op in [abs, min, max]:
    math_safe_dict[op.__name__] = op


class MathNode(Node):
    def __init__(self, var_name, expr, args):
        self.var_name = var_name
        self.expr = expr
        self.args = args

    def render(self, context):
        expr = self.expr
        for i, a in enumerate(self.args):
            expr = expr.replace('$%d' % (i + 1), str(a.resolve(context)))
        try:
            result = eval(expr, {"__builtins__": None}, math_safe_dict)
            context[self.var_name] = result
        except:
            pass
        return ''
            

@register.tag('math')
def do_math(parser, token):
    """
    Syntax:
        {% math <argument, ..> "expression" as var_name %}

    Evaluates a math expression in the current context and saves the value into a variable with the given name.

    "$<number>" is a placeholder in the math expression. It will be replaced by the value of the argument at index <number> - 1. 
    Arguments are static values or variables immediately after 'math' tag and before the expression (the third last token).

    Example usage,
        {% math a b "min($1, $2)" as result %}
        {% math a|length b|length 3 "($1 + $2) % $3" as result %}
    """
    tokens = token.split_contents()
    if len(tokens) < 5:
        raise TemplateSyntaxError("'math' tag requires at least 4 arguments")
    expr, as_, var_name = tokens[-3:]

    # strip quote if found
    if re.match(r'^(\'|")', expr):
        expr = expr.strip(expr[0])

    args = []
    for a in tokens[1:-3]:
        if a.find('|') != -1:
            args.append(FilterExpression(a, parser))
        else:
            args.append(Variable(a))
    return MathNode(var_name, expr, args)