from operator import attrgetter

from django.test import SimpleTestCase

from judge.utils.ranker import ranker, tie_ranker


class TestRank:
    def __init__(self, points, rank=None):
        self.points = points

    @property
    def neg(self):
        return -self.points


class RankerTestCase(SimpleTestCase):
    def test_ranker(self):
        a, b, c, d, e = TestRank(-1), TestRank(0), TestRank(1), TestRank(1), TestRank(2)

        self.assertEqual(list(ranker([])), [])
        self.assertEqual(list(ranker([a])), [(1, a)])
        self.assertEqual(list(ranker([b], rank=1)), [(2, b)])
        self.assertEqual(list(ranker([a, b])), [(1, a), (2, b)])
        self.assertEqual(list(ranker([c, d])), [(1, c), (1, d)])
        self.assertEqual(list(ranker([b, c, d])), [(1, b), (2, c), (2, d)])
        self.assertEqual(list(ranker([c, d, e])), [(1, c), (1, d), (3, e)])
        self.assertEqual(list(ranker([a, b, c, d, e])), [(1, a), (2, b), (3, c), (3, d), (5, e)])
        self.assertEqual(list(ranker([a, b, c, d, e], rank=-1)), [(0, a), (1, b), (2, c), (2, d), (4, e)])
        self.assertEqual(list(ranker([d, c, b, a], key=attrgetter('neg'), rank=-1)), [(0, d), (0, c), (2, b), (3, a)])

    def test_tie_ranker(self):
        a, b, c, d, e, f = TestRank(-1), TestRank(0), TestRank(1), TestRank(1), TestRank(1), TestRank(2)

        self.assertEqual(list(tie_ranker([])), [])
        self.assertEqual(list(tie_ranker([a])), [(1, a)])
        self.assertEqual(list(tie_ranker([a, b])), [(1, a), (2, b)])
        self.assertEqual(list(tie_ranker([c, d])), [(1.5, c), (1.5, d)])
        self.assertEqual(list(tie_ranker([b, c, d])), [(1, b), (2.5, c), (2.5, d)])
        self.assertEqual(list(tie_ranker([c, d, e])), [(2, c), (2, d), (2, e)])
        self.assertEqual(list(tie_ranker([d, e, f])), [(1.5, d), (1.5, e), (3, f)])
        self.assertEqual(list(tie_ranker([a, b, c, d, e, f])), [(1, a), (2, b), (4, c), (4, d), (4, e), (6, f)])
        self.assertEqual(list(ranker([d, c, b, a], key=attrgetter('neg'))), [(1, d), (1, c), (3, b), (4, a)])
