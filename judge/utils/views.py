from django.shortcuts import render
from django.views.generic import FormView
from django.views.generic.detail import SingleObjectMixin

from judge.utils.diggpaginator import DiggPaginator


def generic_message(request, title, message, status=None):
    return render(request, 'generic-message.html', {
        'message': message,
        'title': title,
    }, status=status)


def add_file_response(request, response, url_path, file_path, file_object=None):
    if url_path is not None and request.META.get('SERVER_SOFTWARE', '').startswith('nginx/'):
        response['X-Accel-Redirect'] = url_path
    else:
        if file_object is None:
            with open(file_path, 'rb') as f:
                response.content = f.read()
        else:
            with file_object.open(file_path, 'rb') as f:
                response.content = f.read()


def paginate_query_context(request):
    query = request.GET.copy()
    query.setlist('page', [])
    query = query.urlencode()
    if query:
        return {'page_prefix': '%s?%s&page=' % (request.path, query),
                'first_page_href': '%s?%s' % (request.path, query)}
    else:
        return {'page_prefix': '%s?page=' % request.path,
                'first_page_href': request.path}


class NoBatchDeleteMixin(object):
    def get_actions(self, request):
        actions = super(NoBatchDeleteMixin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


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

    def get_default_sort_order(self, request):
        return self.default_sort

    def get(self, request, *args, **kwargs):
        order = request.GET.get('order', '')
        if not ((not order.startswith('-') or order.count('-') == 1) and (order.lstrip('-') in self.all_sorts)):
            order = self.get_default_sort_order(request)
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
        order[current] = ' \u25BE' if self.order.startswith('-') else ' \u25B4'
        return {'sort_links': links, 'sort_order': order}

    def get_sort_paginate_context(self):
        return paginate_query_context(self.request)


def short_circuit_middleware(view):
    view.short_circuit_middleware = True
    return view


class SingleObjectFormView(SingleObjectMixin, FormView):
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)
