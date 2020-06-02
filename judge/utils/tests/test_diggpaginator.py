from django.test import SimpleTestCase

from judge.utils.diggpaginator import DiggPaginator, ExPaginator, InvalidPage, QuerySetDiggPaginator


class CeleryTestCase(SimpleTestCase):
    """These tests were implemented from DiggPaginator's documentation."""

    def test_expaginator(self):
        paginator = ExPaginator(range(1, 1000), 10)
        with self.assertRaises(InvalidPage):
            paginator.page(1000)
        self.assertEqual(paginator.page(1000, softlimit=True).number, paginator.page(100).number)
        with self.assertRaises(InvalidPage):
            paginator.page('str')

    def test_diggpaginator_odd_length(self):
        self.assertEqual(str(DiggPaginator(range(1, 1000), 10, body=6).page(1)), '1 2 3 4 5 6 ... 99 100')
        self.assertEqual(str(DiggPaginator(range(1, 1000), 10, body=6).page(100)), '1 2 ... 95 96 97 98 99 100')

    def test_diggpaginator_even_length(self):
        self.assertEqual(str(DiggPaginator(range(1, 1000), 10, body=6).page(1)), '1 2 3 4 5 6 ... 99 100')
        self.assertEqual(str(DiggPaginator(range(1, 1000), 10, body=6).page(100)), '1 2 ... 95 96 97 98 99 100')

    def test_diggpaginator_leading_main_range(self):
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, padding=2, margin=2).page(3)), '1 2 3 4 5 ... 99 100',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=6, padding=2, margin=2).page(4)), '1 2 3 4 5 6 ... 99 100',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, padding=1, margin=2).page(6)), '1 2 3 4 5 6 7 ... 99 100',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, padding=2, margin=2).page(7)), '1 2 ... 5 6 7 8 9 ... 99 100',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, padding=1, margin=2).page(7)), '1 2 ... 5 6 7 8 9 ... 99 100',
        )

    def test_diggpaginator_trailing_range(self):
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, padding=2, margin=2).page(98)),
            '1 2 ... 96 97 98 99 100',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=6, padding=2, margin=2).page(97)),
            '1 2 ... 95 96 97 98 99 100',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, padding=1, margin=2).page(95)),
            '1 2 ... 94 95 96 97 98 99 100',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, padding=2, margin=2).page(94)),
            '1 2 ... 92 93 94 95 96 ... 99 100',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, padding=1, margin=2).page(94)),
            '1 2 ... 92 93 94 95 96 ... 99 100',
        )

    def test_diggpaginator_all_ranges(self):
        self.assertEqual(
            str(DiggPaginator(range(1, 151), 10, body=6, padding=2).page(7)), '1 2 3 4 5 6 7 8 9 ... 14 15',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 151), 10, body=6, padding=2).page(8)), '1 2 3 4 5 6 7 8 9 10 11 12 13 14 15',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 151), 10, body=6, padding=1).page(8)), '1 2 3 4 5 6 7 8 9 ... 14 15',
        )

    def test_diggpaginator_no_range(self):
        self.assertEqual(str(DiggPaginator(range(1, 80), 10, body=10).page(1)), '1 2 3 4 5 6 7 8')
        self.assertEqual(str(DiggPaginator(range(1, 80), 10, body=10).page(8)), '1 2 3 4 5 6 7 8')
        self.assertEqual(str(DiggPaginator(range(1, 12), 10, body=5).page(1)), '1 2')

    def test_diggpaginator_left_align(self):
        self.assertEqual(str(DiggPaginator(range(1, 1000), 10, body=5, align_left=True).page(1)), '1 2 3 4 5')
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, align_left=True).page(50)), '1 2 ... 48 49 50 51 52',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, align_left=True).page(97)), '1 2 ... 95 96 97 98 99',
        )
        self.assertEqual(
            str(DiggPaginator(range(1, 1000), 10, body=5, align_left=True).page(100)), '1 2 ... 96 97 98 99 100',
        )

    def test_diggpaginator_padding_default(self):
        self.assertEqual(str(DiggPaginator(range(1, 1000), 10, body=10).padding), '4')

    def test_diggpaginator_padding_automatic_reduction(self):
        self.assertEqual(str(DiggPaginator(range(1, 1000), 10, body=5).padding), '2')
        self.assertEqual(str(DiggPaginator(range(1, 1000), 10, body=6).padding), '2')

    def test_diggpaginator_padding_sanity_check(self):
        with self.assertRaisesRegex(ValueError, 'padding too large'):
            DiggPaginator(range(1, 1000), 10, body=5, padding=3)

    def test_querysetdiggpaginator(self):
        self.assertEqual(QuerySetDiggPaginator, DiggPaginator)
