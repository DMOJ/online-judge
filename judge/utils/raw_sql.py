from copy import copy

from django.db import connections
from django.db.models import Field
from django.db.models.expressions import RawSQL
from django.db.models.sql.constants import LOUTER, INNER
from django.db.models.sql.datastructures import Join
from django.utils import six

from judge.utils.cachedict import CacheDict


def unique_together_left_join(queryset, model, link_field_name, filter_field_name, filter_value, parent_model=None):
    link_field = copy(model._meta.get_field(link_field_name).remote_field)
    filter_field = model._meta.get_field(filter_field_name)

    def restrictions(where_class, alias, related_alias):
        cond = where_class()
        cond.add(filter_field.get_lookup('exact')(filter_field.get_col(alias), filter_value), 'AND')
        return cond

    link_field.get_extra_restriction = restrictions

    if parent_model is not None:
        parent_alias = parent_model._meta.db_table
    else:
        parent_alias = queryset.query.get_initial_alias()
    return queryset.query.join(Join(model._meta.db_table, parent_alias, None, LOUTER, link_field, True))


def RawSQLColumn(model, field=None):
    if isinstance(model, Field):
        field = model
        model = field.model
    if isinstance(field, six.string_types):
        field = model._meta.get_field(field)
    return RawSQL('%s.%s' % (model._meta.db_table, field.get_attname_column()[1]), ())


def make_straight_join_query(QueryType):
    class Query(QueryType):
        def join(self, join, *args, **kwargs):
            alias = super().join(join, *args, **kwargs)
            join = self.alias_map[alias]
            if join.join_type == INNER:
                join.join_type = 'STRAIGHT_JOIN'
            return alias

    return Query


straight_join_cache = CacheDict(make_straight_join_query)


def use_straight_join(queryset):
    if connections[queryset.db].vendor != 'mysql':
        return
    try:
        cloner = queryset.query.chain
    except AttributeError:
        cloner = queryset.query.clone
    queryset.query = cloner(straight_join_cache[type(queryset.query)])
