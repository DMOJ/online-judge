from copy import copy

from django.db.models.sql.constants import LOUTER
from django.db.models.sql.datastructures import Join


def unique_together_left_join(queryset, model, link_field_name, filter_field_name, filter_value):
    link_field = copy(model._meta.get_field(link_field_name).rel)
    filter_field = model._meta.get_field(filter_field_name)

    def restrictions(where_class, alias, related_alias):
        cond = where_class()
        cond.add(filter_field.get_lookup('exact')(filter_field.get_col(alias), filter_value), 'AND')
        return cond

    link_field.get_extra_restriction = restrictions
    queryset.query.join(Join(model._meta.db_table, queryset.query.get_initial_alias(), None, LOUTER, link_field, True))
