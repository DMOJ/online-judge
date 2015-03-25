# From: http://www.mercurytide.co.uk/news/article/django-full-text-search/

from django.db import models, connection
from django.db.models.query import QuerySet


class SearchQuerySet(QuerySet):
    def __init__(self, fields=None, **kwargs):
        super(SearchQuerySet, self).__init__(**kwargs)
        self._search_fields = fields

    def _clone(self, *args, **kwargs):
        queryset = super(SearchQuerySet, self)._clone(*args, **kwargs)
        queryset._search_fields = self._search_fields
        return queryset

    def search(self, query):
        meta = self.model._meta

        # Get the table name and column names from the model
        # in `table_name`.`column_name` style
        columns = [meta.get_field(name, many_to_many=False).column for name in self._search_fields]
        full_names = ['%s.%s' %
                      (connection.ops.quote_name(meta.db_table),
                       connection.ops.quote_name(column))
                      for column in columns]

        # Create the MATCH...AGAINST expressions
        fulltext_columns = ', '.join(full_names)
        match_expr = ('MATCH(%s) AGAINST (%%s)' % fulltext_columns)

        # Add the extra SELECT and WHERE options
        return self.extra(select={'relevance': match_expr},
                          select_params=[query],
                          where=[match_expr],
                          params=[query])


class SearchManager(models.Manager):
    def __init__(self, fields=None):
        super(SearchManager, self).__init__()
        self._search_fields = fields

    def get_queryset(self):
        if self._search_fields is not None:
            return SearchQuerySet(model=self.model, fields=self._search_fields)
        return super(SearchManager, self).get_queryset()

    def search(self, query):
        return self.get_queryset().search(query)
