import collections.abc
import inspect
from math import ceil

from django.core.paginator import EmptyPage, InvalidPage
from django.http import Http404
from django.utils.functional import cached_property
from django.utils.inspect import method_has_no_args


class InfinitePage(collections.abc.Sequence):
    def __init__(self, object_list, number, unfiltered_queryset, page_size, pad_pages, paginator):
        self.object_list = list(object_list)
        self.number = number
        self.unfiltered_queryset = unfiltered_queryset
        self.page_size = page_size
        self.pad_pages = pad_pages
        self.num_pages = 1e3000
        self.paginator = paginator

    def __repr__(self):
        return '<Page %s of many>' % self.number

    def __len__(self):
        return len(self.object_list)

    def __getitem__(self, index):
        return self.object_list[index]

    @cached_property
    def _after_up_to_pad(self):
        first_after = self.number * self.page_size
        padding_length = self.pad_pages * self.page_size
        queryset = self.unfiltered_queryset[first_after:first_after + padding_length + 1]
        c = getattr(queryset, 'count', None)
        if callable(c) and not inspect.isbuiltin(c) and method_has_no_args(c):
            return c()
        return len(queryset)

    def has_next(self):
        return self._after_up_to_pad > 0

    def has_previous(self):
        return self.number > 1

    def has_other_pages(self):
        return self.has_previous() or self.has_next()

    def next_page_number(self):
        if not self.has_next():
            raise EmptyPage()
        return self.number + 1

    def previous_page_number(self):
        if self.number <= 1:
            raise EmptyPage()
        return self.number - 1

    def start_index(self):
        return (self.page_size * (self.number - 1)) + 1

    def end_index(self):
        return self.start_index() + len(self.object_list)

    @cached_property
    def main_range(self):
        start = max(1, self.number - self.pad_pages)
        end = self.number + min(int(ceil(self._after_up_to_pad / self.page_size)), self.pad_pages)
        return range(start, end + 1)

    @cached_property
    def leading_range(self):
        return range(1, min(3, self.main_range[0]))

    @cached_property
    def has_trailing(self):
        return self._after_up_to_pad > self.pad_pages * self.page_size

    @cached_property
    def page_range(self):
        result = list(self.leading_range)
        main_range = self.main_range

        # Add ... element if there is space in between.
        if result and result[-1] + 1 < self.main_range[0]:
            result.append(False)

        result += list(main_range)

        # Add ... element if there are elements after main_range.
        if self.has_trailing:
            result.append(False)
        return result


class DummyPaginator:
    is_infinite = True

    def __init__(self, per_page):
        self.per_page = per_page


def infinite_paginate(queryset, page, page_size, pad_pages, paginator=None):
    if page < 1:
        raise EmptyPage()
    sliced = queryset[(page - 1) * page_size:page * page_size]
    if page > 1 and not sliced:
        raise EmptyPage()
    return InfinitePage(sliced, page, queryset, page_size, pad_pages, paginator)


class InfinitePaginationMixin:
    pad_pages = 2

    @property
    def use_infinite_pagination(self):
        return True

    def paginate_queryset(self, queryset, page_size):
        if not self.use_infinite_pagination:
            paginator, page, object_list, has_other = super().paginate_queryset(queryset, page_size)
            paginator.is_infinite = False
            return paginator, page, object_list, has_other

        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        try:
            page_number = int(page)
        except ValueError:
            raise Http404('Page cannot be converted to an int.')
        try:
            paginator = DummyPaginator(page_size)
            page = infinite_paginate(queryset, page_number, page_size, self.pad_pages, paginator)
            return paginator, page, page.object_list, page.has_other_pages()
        except InvalidPage as e:
            raise Http404('Invalid page (%(page_number)s): %(message)s' % {
                'page_number': page_number,
                'message': str(e),
            })
