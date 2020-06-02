from django.test import SimpleTestCase

from judge.utils.infinite_paginator import infinite_paginate


class InfinitePaginatorTestCase(SimpleTestCase):
    def test_first_page(self):
        self.assertEqual(infinite_paginate(range(1, 101), 1, 10, 2).object_list, list(range(1, 11)))

        self.assertEqual(infinite_paginate(range(1, 101), 1, 10, 2).page_range, [1, 2, 3, False])
        self.assertEqual(infinite_paginate(range(1, 31), 1, 10, 2).page_range, [1, 2, 3])
        self.assertEqual(infinite_paginate(range(1, 22), 1, 10, 2).page_range, [1, 2, 3])
        self.assertEqual(infinite_paginate(range(1, 21), 1, 10, 2).page_range, [1, 2])
        self.assertEqual(infinite_paginate(range(1, 12), 1, 10, 2).page_range, [1, 2])
        self.assertEqual(infinite_paginate(range(1, 11), 1, 10, 2).page_range, [1])
        self.assertEqual(infinite_paginate(range(1, 2), 1, 10, 2).page_range, [1])
        self.assertEqual(infinite_paginate([], 1, 10, 2).page_range, [1])

    def test_gaps(self):
        self.assertEqual(infinite_paginate(range(1, 101), 1, 10, 2).page_range, [1, 2, 3, False])
        self.assertEqual(infinite_paginate(range(1, 101), 2, 10, 2).page_range, [1, 2, 3, 4, False])
        self.assertEqual(infinite_paginate(range(1, 101), 3, 10, 2).page_range, [1, 2, 3, 4, 5, False])
        self.assertEqual(infinite_paginate(range(1, 101), 5, 10, 2).page_range, [1, 2, 3, 4, 5, 6, 7, False])
        self.assertEqual(infinite_paginate(range(1, 101), 6, 10, 2).page_range, [1, 2, False, 4, 5, 6, 7, 8, False])

    def test_end(self):
        self.assertEqual(infinite_paginate(range(1, 101), 7, 10, 2).page_range, [1, 2, False, 5, 6, 7, 8, 9, False])
        self.assertEqual(infinite_paginate(range(1, 101), 8, 10, 2).page_range, [1, 2, False, 6, 7, 8, 9, 10])
        self.assertEqual(infinite_paginate(range(1, 101), 9, 10, 2).page_range, [1, 2, False, 7, 8, 9, 10])
        self.assertEqual(infinite_paginate(range(1, 101), 10, 10, 2).page_range, [1, 2, False, 8, 9, 10])
        self.assertEqual(infinite_paginate(range(1, 100), 10, 10, 2).page_range, [1, 2, False, 8, 9, 10])
        self.assertEqual(infinite_paginate(range(1, 100), 10, 10, 2).object_list, list(range(91, 100)))
