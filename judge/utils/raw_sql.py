from copy import copy

from django.db import connections
from django.db.models import Field
from django.db.models.expressions import RawSQL
from django.db.models.sql.constants import INNER, LOUTER
from django.db.models.sql.datastructures import Join

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


class RawSQLJoin(Join):
    def __init__(self, subquery, subquery_params, parent_alias, table_alias, join_type, join_field, nullable,
                 filtered_relation=None):
        self.subquery_params = subquery_params
        super().__init__(subquery, parent_alias, table_alias, join_type, join_field, nullable, filtered_relation)

    def as_sql(self, compiler, connection):
        compiler.quote_cache[self.table_name] = '(%s)' % self.table_name
        sql, params = super().as_sql(compiler, connection)
        return sql, self.subquery_params + params


class FakeJoinField:
    def __init__(self, joining_columns):
        self.joining_columns = joining_columns

    def get_joining_columns(self):
        return self.joining_columns

    def get_extra_restriction(self, where_class, alias, remote_alias):
        pass


def join_sql_subquery(queryset, subquery, params, join_fields, alias, join_type=INNER, parent_model=None):
    if parent_model is not None:
        parent_alias = parent_model._meta.db_table
    else:
        parent_alias = queryset.query.get_initial_alias()
    if isinstance(queryset.query.external_aliases, dict):  # Django 3.x
        queryset.query.external_aliases[alias] = True
    else:
        queryset.query.external_aliases.add(alias)
    join = RawSQLJoin(subquery, params, parent_alias, alias, join_type, FakeJoinField(join_fields), join_type == LOUTER)
    queryset.query.join(join)
    join.table_alias = alias


def RawSQLColumn(model, field=None, output_field=None):
    if isinstance(model, Field):
        field = model
        model = field.model
    if isinstance(field, str):
        field = model._meta.get_field(field)
    return RawSQL('%s.%s' % (model._meta.db_table, field.get_attname_column()[1]), (), output_field=output_field)


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
