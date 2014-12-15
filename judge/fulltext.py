# From: http://www.mercurytide.co.uk/news/article/django-full-text-search/

from django.db import models, backend
from django.db.models.query import QuerySet


class SearchQuerySet(QuerySet):
    def __init__(self, model=None, query=None, using=None, fields=None):
        super(SearchQuerySet, self).__init__(model, query, using)
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
                      (backend.quote_name(meta.db_table),
                       backend.quote_name(column))
                      for column in columns]

        # Create the MATCH...AGAINST expressions
        fulltext_columns = ', '.join(full_names)
        match_expr = ('MATCH(%s) AGAINST (%%s)' % fulltext_columns)

        # Add the extra SELECT and WHERE options
        return self.extra(select={'relevance': match_expr},
                          where=[match_expr],
                          params=[query, query])


class SearchManager(models.Manager):
    def __init__(self, fields):
        super(SearchManager, self).__init__()
        self._search_fields = fields

    def get_queryset(self):
        return SearchQuerySet(self.model, fields=self._search_fields)

    def search(self, query):
        return self.get_queryset().search(query)
