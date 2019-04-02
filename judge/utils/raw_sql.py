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
        def __init__(self):
            """
            This class can only be created from factory function
            """

        def join(self, join, reuse=None, reuse_with_filtered_relation=False):
            alias = super(Query, self).join(join, reuse, reuse_with_filtered_relation)
            alias = super(Query, self).join(join, reuse)
            join = self.alias_map[alias]
            if join.join_type == INNER:
                join.join_type = 'STRAIGHT_JOIN'
            return alias

    return Query


straight_join_cache = CacheDict(make_straight_join_query)


# Source: SchOJ's PY3 port
def clone_to_new(old_query):
    """
    Return a copy of the current Query. A lightweight alternative to
    to deepcopy().
    """
    obj = straight_join_cache[type(old_query)]()
    # Copy references to everything.
    obj.__class__ = old_query.__class__
    obj.__dict__ = old_query.__dict__.copy()
    # Clone attributes that can't use shallow copy.
    obj.alias_refcount = old_query.alias_refcount.copy()
    obj.alias_map = old_query.alias_map.copy()
    obj.external_aliases = old_query.external_aliases.copy()
    obj.table_map = old_query.table_map.copy()
    obj.where = old_query.where.clone()
    obj._annotations = old_query._annotations.copy() if old_query._annotations is not None else None
    if old_query.annotation_select_mask is None:
        obj.annotation_select_mask = None
    else:
        obj.annotation_select_mask = old_query.annotation_select_mask.copy()
    # _annotation_select_cache cannot be copied, as doing so breaks the
    # (necessary) state in which both annotations and
    # _annotation_select_cache point to the same underlying objects.
    # It will get re-populated in the cloned queryset the next time it's
    # used.
    obj._annotation_select_cache = None
    obj._extra = old_query._extra.copy() if old_query._extra is not None else None
    if old_query.extra_select_mask is None:
        obj.extra_select_mask = None
    else:
        obj.extra_select_mask = old_query.extra_select_mask.copy()
    if old_query._extra_select_cache is None:
        obj._extra_select_cache = None
    else:
        obj._extra_select_cache = old_query._extra_select_cache.copy()
    if 'subq_aliases' in old_query.__dict__:
        obj.subq_aliases = old_query.subq_aliases.copy()
    obj.used_aliases = old_query.used_aliases.copy()
    obj._filtered_relations = old_query._filtered_relations.copy()
    # Clear the cached_property
    try:
        del obj.base_table
    except AttributeError:
        pass
    assert (type(obj) == type(old_query))
    return obj


def use_straight_join(queryset):
    if connections[queryset.db].vendor != 'mysql':
        return
    queryset.query = clone_to_new(queryset.query)
