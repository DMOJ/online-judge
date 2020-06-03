from django.test import SimpleTestCase

from judge.utils.cachedict import CacheDict


class CacheDictTestCase(SimpleTestCase):
    def setUp(self):
        self.test_dict = {'a': True}
        self.cache_dict = CacheDict(lambda id: self.test_dict[id])

    def test_original_item_in_cachedict(self):
        self.assertNotIn('a', self.cache_dict)
        self.assertTrue(self.cache_dict['a'])
        self.assertIn('a', self.cache_dict)

    def test_new_item_in_cachedict(self):
        self.test_dict['b'] = True
        self.assertNotIn('b', self.cache_dict)
        self.assertTrue(self.cache_dict['b'])
        self.assertIn('b', self.cache_dict)
