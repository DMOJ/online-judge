import unittest

from judge.utils.lazy import memo_lazy


class MemoLazyTestCase(unittest.TestCase):
    def test_works(self):
        called_times = 0

        def work():
            nonlocal called_times
            called_times += 1
            return 123

        result = memo_lazy(work, int)
        self.assertEqual(result, 123)
        self.assertEqual(result + 123, 246)
        self.assertEqual(called_times, 1)
