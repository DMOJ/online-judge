from django.shortcuts import render

from dmoj import settings
from judge.utils.diggpaginator import DiggPaginator


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
