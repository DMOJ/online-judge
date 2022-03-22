import unittest
from itertools import chain

from judge.utils.iterator import chunk


class ChunkTestCase(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(list(chunk([], 5)), [])

    def test_normal(self):
        for size in [10, 13, 100, 200]:
            with self.subTest(f'chunk size {size}'):
                result = list(chunk(range(100), size))
                self.assertEqual(list(chain(*result)), list(range(100)))
                for part in result[:-1]:
                    self.assertEqual(len(part), size)
                self.assertLessEqual(len(result[-1]), size)
