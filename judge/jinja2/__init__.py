from django_jinja import library
from mptt.utils import get_cached_trees
from statici18n.templatetags.statici18n import inlinei18n

from judge.user_translations import ugettext
from . import language, gravatar, rating, markdown, reference

library.global_function('str', unicode)
library.filter('str', unicode)
library.global_function('inlinei18n', inlinei18n)
library.global_function('mptt_tree', get_cached_trees)
library.global_function('user_trans', ugettext)
