from operator import attrgetter
from django import template
from django.core.cache import cache
from judge.models import Language, Problem, Profile

register = template.Library()


class DataNode(template.Node):
    model = None
    prefix = None
    ttl = 3600

    def __init__(self, problem):
        self.problem_id = template.Variable(problem)

    def get_data(self, instance):
        raise NotImplementedError

    def render(self, context):
        id = int(self.problem_id.resolve(context))
        key = '%s:%d' % (self.prefix, id)
        result = cache.get(key)
        if result is not None:
            return result
        instance = self.model.objects.get(id=id)
        result = self.get_data(instance)
        cache.set(key, result, self.ttl)
        return result


def register_data_tag(name, cls, model_name):
    def tag(parser, token):
        try:
            return cls(token.split_contents()[1])
        except IndexError:
            raise template.TemplateSyntaxError('%r tag requires %s id' % (token.contents.split()[0], model_name))
    register.tag(name, tag)


class LanguageShortDisplayNode(DataNode):
    model = Language
    prefix = 'lang_sdn'

    def get_data(self, language):
        return language.short_display_name


class ProblemCodeNode(DataNode):
    model = Problem
    prefix = 'prob_code'

    def get_data(self, problem):
        return problem.code


class ProblemNameNode(DataNode):
    model = Problem
    prefix = 'prob_name'

    def get_data(self, problem):
        return problem.name

register_data_tag('language_short_display', LanguageShortDisplayNode, 'language')
register_data_tag('problem_code', ProblemCodeNode, 'problem')
register_data_tag('problem_name', ProblemNameNode, 'problem')


def make_problem_data_filter(prefix, model, getter, ttl=3600):
    def filter(problem):
        id = int(problem)
        key = '%s:%d' % (prefix, id)
        result = cache.get(key)
        if result is not None:
            return result
        result = getter(model.objects.get(id=id))
        cache.set(key, result, ttl)
        return result
    return filter

register.filter('problem_code', make_problem_data_filter('prob_code', Problem, attrgetter('code')))