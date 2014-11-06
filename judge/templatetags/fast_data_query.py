from operator import attrgetter
from django import template
from django.core.cache import cache
from judge.models import Language, Problem

register = template.Library()


class LanguageShortDisplayNode(template.Node):
    def __init__(self, language):
        self.language_id = template.Variable(language)
 
    def render(self, context):
        id = int(self.language_id.resolve(context))
        key = 'lang_sdn:%d' % id
        result = cache.get(key)
        if result is not None:
            return result
        result = Language.objects.get(id=id).short_display_name
        cache.set(key, result, 86400)
        return result
 
@register.tag
def language_short_display(parser, token):
    try:
        return LanguageShortDisplayNode(token.split_contents()[1])
    except IndexError:
        raise template.TemplateSyntaxError('%r tag requires language id' % token.contents.split()[0])


class ProblemDataNode(template.Node):
    def __init__(self, problem):
        self.problem_id = template.Variable(problem)

    def field_name(self):
        raise NotImplementedError

    def get_data(self, problem):
        raise NotImplementedError

    def time_to_live(self, problem):
        return 3600

    def render(self, context):
        id = int(self.problem_id.resolve(context))
        key = 'prob_%s:%d' % (self.field_name(), id)
        result = cache.get(key)
        if result is not None:
            return result
        problem = Problem.objects.get(id=id)
        result = self.get_data(problem)
        cache.set(key, result, self.time_to_live(problem))
        return result


class ProblemCodeNode(ProblemDataNode):
    def field_name(self):
        return 'code'

    def get_data(self, problem):
        return problem.code


@register.tag
def problem_code(parser, token):
    try:
        return ProblemCodeNode(token.split_contents()[1])
    except IndexError:
        raise template.TemplateSyntaxError('%r tag requires problem id' % token.contents.split()[0])


class ProblemNameNode(ProblemDataNode):
    def field_name(self):
        return 'name'

    def get_data(self, problem):
        return problem.name


@register.tag
def problem_name(parser, token):
    try:
        return ProblemNameNode(token.split_contents()[1])
    except IndexError:
        raise template.TemplateSyntaxError('%r tag requires problem id' % token.contents.split()[0])


def make_problem_data_filter(name, getter, ttl=3600):
    def filter(problem):
        id = int(problem)
        key = 'prob_%s:%d' % (name, id)
        result = cache.get(key)
        if result is not None:
            return result
        result = getter(Problem.objects.get(id=id))
        cache.set(key, result, ttl)
        return result
    return filter

register.filter('problem_code', make_problem_data_filter('code', attrgetter('code')))
