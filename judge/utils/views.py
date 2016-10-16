from django.shortcuts import render
from django.utils.decorators import method_decorator

from dmoj import settings
from judge.utils.diggpaginator import DiggPaginator


def class_view_decorator(function_decorator):
    """Convert a function based decorator into a class based decorator usable
    on class based Views.

    Can't subclass the `View` as it breaks inheritance (super in particular),
    so we monkey-patch instead.
    """

    def simple_decorator(View):
        View.dispatch = method_decorator(function_decorator)(View.dispatch)
        return View

    return simple_decorator


def generic_message(request, title, message, status=None):
    return render(request, 'generic_message.jade', {
        'message': message,
        'title': title
    }, status=status)


class LoadSelect2Mixin(object):
    def get_context_data(self, **kwargs):
        context = super(LoadSelect2Mixin, self).get_context_data(**kwargs)

        select2_css = getattr(settings, 'SELECT2_CSS_URL', None)
        select2_js = getattr(settings, 'SELECT2_JS_URL', None)
        has_select2 = select2_css is not None and select2_js is not None
        context['has_select2'] = has_select2
        if has_select2:
            context['SELECT2_CSS_URL'] = select2_css
            context['SELECT2_JS_URL'] = select2_js
        return context


class TitleMixin(object):
    title = '(untitled)'
    content_title = None

    def get_context_data(self, **kwargs):
        context = super(TitleMixin, self).get_context_data(**kwargs)
        context['title'] = self.get_title()
        content_title = self.get_content_title()
        if content_title is not None:
            context['content_title'] = content_title
        return context

    def get_content_title(self):
        return self.content_title

    def get_title(self):
        return self.title


class DiggPaginatorMixin(object):
    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        return DiggPaginator(queryset, per_page, body=6, padding=2,
                             orphans=orphans, allow_empty_first_page=allow_empty_first_page, **kwargs)


class QueryStringSortMixin(object):
    all_sorts = None
    default_sort = None
    default_desc = ()

    def get(self, request, *args, **kwargs):
        order = request.GET.get('order', '')
        if not ((not order.startswith('-') or order.count('-') == 1) and (order.lstrip('-') in self.all_sorts)):
            order = self.default_sort
        self.order = order

        return super(QueryStringSortMixin, self).get(request, *args, **kwargs)

    def get_sort_context(self):
        query = self.request.GET.copy()
        query.setlist('order', [])
        query = query.urlencode()
        sort_prefix = '%s?%s&order=' % (self.request.path, query) if query else '%s?order=' % self.request.path
        current = self.order.lstrip('-')

        links = {key: sort_prefix + ('-' if key in self.default_desc else '') + key for key in self.all_sorts}
        links[current] = sort_prefix + ('' if self.order.startswith('-') else '-') + current

        order = {key: '' for key in self.all_sorts}
        order[current] = u' \u25BE' if self.order.startswith('-') else u' \u25B4'
        return {'sort_links': links, 'sort_order': order}

    def get_sort_paginate_context(self):
        query = self.request.GET.copy()
        query.setlist('page', [])
        query = query.urlencode()
        if query:
            return {'page_prefix': '%s?%s&page=' % (self.request.path, query),
                    'first_page_href': '%s?%s' % (self.request.path, query)}
        else:
            return {'page_prefix': '%s?page=' % self.request.path,
                    'first_page_href': self.request.path}
