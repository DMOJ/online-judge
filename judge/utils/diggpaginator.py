import math
from functools import reduce

from django.core.paginator import InvalidPage, Page, Paginator

__all__ = (
    'InvalidPage',
    'ExPaginator',
    'DiggPaginator',
    'QuerySetDiggPaginator',
)


class ExPaginator(Paginator):
    """Adds a ``softlimit`` option to ``page()``. If True, querying a
    page number larger than max. will not fail, but instead return the
    last available page.

    This is useful when the data source can not provide an exact count
    at all times (like some search engines), meaning the user could
    possibly see links to invalid pages at some point which we wouldn't
    want to fail as 404s.

    >>> items = range(1, 1000)
    >>> paginator = ExPaginator(items, 10)
    >>> paginator.page(1000)
    Traceback (most recent call last):
    InvalidPage: That page contains no results
    >>> paginator.page(1000, softlimit=True)
    <Page 100 of 100>

    # [bug] graceful handling of non-int args
    >>> paginator.page("str")
    Traceback (most recent call last):
    InvalidPage: That page number is not an integer
    """

    def _ensure_int(self, num, e):
        # see Django #7307
        try:
            return int(num)
        except ValueError:
            raise e

    def page(self, number, softlimit=False):
        try:
            return super(ExPaginator, self).page(number)
        except InvalidPage as e:
            number = self._ensure_int(number, e)
            if number > self.num_pages and softlimit:
                return self.page(self.num_pages, softlimit=False)
            else:
                raise e


class DiggPaginator(ExPaginator):
    """
    Based on Django's default paginator, it adds "Digg-style" page ranges
    with a leading block of pages, an optional middle block, and another
    block at the end of the page range. They are available as attributes
    on the page:

    {# with: page = digg_paginator.page(1) #}
    {% for num in page.leading_range %} ...
    {% for num in page.main_range %} ...
    {% for num in page.trailing_range %} ...

    Additionally, ``page_range`` contains a nun-numeric ``False`` element
    for every transition between two ranges.

    {% for num in page.page_range %}
        {% if not num %} ...  {# literally output dots #}
        {% else %}{{ num }}
        {% endif %}
    {% endfor %}

    Additional arguments passed to the constructor allow customization of
    how those bocks are constructed:

    body=5, tail=2

    [1] 2 3 4 5 ... 91 92
    |_________|     |___|
    body            tail
              |_____|
              margin

    body=5, tail=2, padding=2

    1 2 ... 6 7 [8] 9 10 ... 91 92
            |_|     |__|
             ^padding^
    |_|     |__________|     |___|
    tail    body             tail

    ``margin`` is the minimum number of pages required between two ranges; if
    there are less, they are combined into one.

    When ``align_left`` is set to ``True``, the paginator operates in a
    special mode that always skips the right tail, e.g. does not display the
    end block unless necessary. This is useful for situations in which the
    exact number of items/pages is not actually known.

    # odd body length
    >>> print DiggPaginator(range(1,1000), 10, body=5).page(1)
    1 2 3 4 5 ... 99 100
    >>> print DiggPaginator(range(1,1000), 10, body=5).page(100)
    1 2 ... 96 97 98 99 100

    # even body length
    >>> print DiggPaginator(range(1,1000), 10, body=6).page(1)
    1 2 3 4 5 6 ... 99 100
    >>> print DiggPaginator(range(1,1000), 10, body=6).page(100)
    1 2 ... 95 96 97 98 99 100

    # leading range and main range are combined when close; note how
    # we have varying body and padding values, and their effect.
    >>> print DiggPaginator(range(1,1000), 10, body=5, padding=2, margin=2).page(3)
    1 2 3 4 5 ... 99 100
    >>> print DiggPaginator(range(1,1000), 10, body=6, padding=2, margin=2).page(4)
    1 2 3 4 5 6 ... 99 100
    >>> print DiggPaginator(range(1,1000), 10, body=5, padding=1, margin=2).page(6)
    1 2 3 4 5 6 7 ... 99 100
    >>> print DiggPaginator(range(1,1000), 10, body=5, padding=2, margin=2).page(7)
    1 2 ... 5 6 7 8 9 ... 99 100
    >>> print DiggPaginator(range(1,1000), 10, body=5, padding=1, margin=2).page(7)
    1 2 ... 5 6 7 8 9 ... 99 100

    # the trailing range works the same
    >>> print DiggPaginator(range(1,1000), 10, body=5, padding=2, margin=2, ).page(98)
    1 2 ... 96 97 98 99 100
    >>> print DiggPaginator(range(1,1000), 10, body=6, padding=2, margin=2, ).page(97)
    1 2 ... 95 96 97 98 99 100
    >>> print DiggPaginator(range(1,1000), 10, body=5, padding=1, margin=2, ).page(95)
    1 2 ... 94 95 96 97 98 99 100
    >>> print DiggPaginator(range(1,1000), 10, body=5, padding=2, margin=2, ).page(94)
    1 2 ... 92 93 94 95 96 ... 99 100
    >>> print DiggPaginator(range(1,1000), 10, body=5, padding=1, margin=2, ).page(94)
    1 2 ... 92 93 94 95 96 ... 99 100

    # all three ranges may be combined as well
    >>> print DiggPaginator(range(1,151), 10, body=6, padding=2).page(7)
    1 2 3 4 5 6 7 8 9 ... 14 15
    >>> print DiggPaginator(range(1,151), 10, body=6, padding=2).page(8)
    1 2 3 4 5 6 7 8 9 10 11 12 13 14 15
    >>> print DiggPaginator(range(1,151), 10, body=6, padding=1).page(8)
    1 2 3 4 5 6 7 8 9 ... 14 15

    # no leading or trailing ranges might be required if there are only
    # a very small number of pages
    >>> print DiggPaginator(range(1,80), 10, body=10).page(1)
    1 2 3 4 5 6 7 8
    >>> print DiggPaginator(range(1,80), 10, body=10).page(8)
    1 2 3 4 5 6 7 8
    >>> print DiggPaginator(range(1,12), 10, body=5).page(1)
    1 2

    # test left align mode
    >>> print DiggPaginator(range(1,1000), 10, body=5, align_left=True).page(1)
    1 2 3 4 5
    >>> print DiggPaginator(range(1,1000), 10, body=5, align_left=True).page(50)
    1 2 ... 48 49 50 51 52
    >>> print DiggPaginator(range(1,1000), 10, body=5, align_left=True).page(97)
    1 2 ... 95 96 97 98 99
    >>> print DiggPaginator(range(1,1000), 10, body=5, align_left=True).page(100)
    1 2 ... 96 97 98 99 100

    # padding: default value
    >>> DiggPaginator(range(1,1000), 10, body=10).padding
    4

    # padding: automatic reduction
    >>> DiggPaginator(range(1,1000), 10, body=5).padding
    2
    >>> DiggPaginator(range(1,1000), 10, body=6).padding
    2

    # padding: sanity check
    >>> DiggPaginator(range(1,1000), 10, body=5, padding=3)
    Traceback (most recent call last):
    ValueError: padding too large for body (max 2)
    """

    def __init__(self, *args, **kwargs):
        self.body = kwargs.pop('body', 10)
        self.tail = kwargs.pop('tail', 2)
        self.align_left = kwargs.pop('align_left', False)
        self.margin = kwargs.pop('margin', 4)  # TODO: make the default relative to body?
        # validate padding value
        max_padding = int(math.ceil(self.body / 2.0) - 1)
        self.padding = kwargs.pop('padding', min(4, max_padding))
        count_override = kwargs.pop('count', None)
        if count_override is not None:
            self.__dict__['count'] = count_override
        if self.padding > max_padding:
            raise ValueError('padding too large for body (max %d)' % max_padding)
        super(DiggPaginator, self).__init__(*args, **kwargs)

    def page(self, number, *args, **kwargs):
        """Return a standard ``Page`` instance with custom, digg-specific
        page ranges attached.
        """

        page = super(DiggPaginator, self).page(number, *args, **kwargs)
        number = int(number)  # we know this will work

        # easier access
        num_pages, body, tail, padding, margin = \
            self.num_pages, self.body, self.tail, self.padding, self.margin

        # put active page in middle of main range
        main_range = list(map(int, [
            math.floor(number - body / 2.0) + 1,  # +1 = shift odd body to right
            math.floor(number + body / 2.0)]))
        # adjust bounds
        if main_range[0] < 1:
            main_range = list(map(abs(main_range[0] - 1).__add__, main_range))
        if main_range[1] > num_pages:
            main_range = list(map((num_pages - main_range[1]).__add__, main_range))

        # Determine leading and trailing ranges; if possible and appropriate,
        # combine them with the main range, in which case the resulting main
        # block might end up considerable larger than requested. While we
        # can't guarantee the exact size in those cases, we can at least try
        # to come as close as possible: we can reduce the other boundary to
        # max padding, instead of using half the body size, which would
        # otherwise be the case. If the padding is large enough, this will
        # of course have no effect.
        # Example:
        #     total pages=100, page=4, body=5, (default padding=2)
        #     1 2 3 [4] 5 6 ... 99 100
        #     total pages=100, page=4, body=5, padding=1
        #     1 2 3 [4] 5 ... 99 100
        # If it were not for this adjustment, both cases would result in the
        # first output, regardless of the padding value.
        if main_range[0] <= tail + margin:
            leading = []
            main_range = [1, max(body, min(number + padding, main_range[1]))]
            main_range[0] = 1
        else:
            leading = list(range(1, tail + 1))
            # basically same for trailing range, but not in ``left_align`` mode
        if self.align_left:
            trailing = []
        else:
            if main_range[1] >= num_pages - (tail + margin) + 1:
                trailing = []
                if not leading:
                    # ... but handle the special case of neither leading nor
                    # trailing ranges; otherwise, we would now modify the
                    # main range low bound, which we just set in the previous
                    # section, again.
                    main_range = [1, num_pages]
                else:
                    main_range = [min(num_pages - body + 1, max(number - padding, main_range[0])), num_pages]
            else:
                trailing = list(range(num_pages - tail + 1, num_pages + 1))

        # finally, normalize values that are out of bound; this basically
        # fixes all the things the above code screwed up in the simple case
        # of few enough pages where one range would suffice.
        main_range = [max(main_range[0], 1), min(main_range[1], num_pages)]

        # make the result of our calculations available as custom ranges
        # on the ``Page`` instance.
        page.main_range = list(range(main_range[0], main_range[1] + 1))
        page.leading_range = leading
        page.trailing_range = trailing
        page.page_range = reduce(lambda x, y: x + ((x and y) and [False]) + y,
                                 [page.leading_range, page.main_range, page.trailing_range])

        page.__class__ = DiggPage
        return page


class DiggPage(Page):
    def __str__(self):
        return ' ... '.join(filter(None, [
            ' '.join(map(str, self.leading_range)),
            ' '.join(map(str, self.main_range)),
            ' '.join(map(str, self.trailing_range))]))

    @property
    def num_pages(self):
        return self.paginator.num_pages


QuerySetDiggPaginator = DiggPaginator

if __name__ == '__main__':
    import doctest

    doctest.testmod()
