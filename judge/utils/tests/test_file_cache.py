import gzip
import os
import shutil
import tempfile
from io import UnsupportedOperation
from urllib.parse import urljoin

from django.test import SimpleTestCase

from judge.utils.file_cache import HashFileCache


class FileCacheTestCase(SimpleTestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache = HashFileCache(self.temp_dir, 'https://example.com')
        self.gzip_temp_dir = tempfile.mkdtemp()
        self.gzip_cache = HashFileCache(self.gzip_temp_dir, 'https://example.com', gzip=True)

        # This acts as a test for create() as well as setup for other tests
        self.cache.create('foo')
        self.cache.create('foo')
        self.gzip_cache.create('foo')
        self.gzip_cache.create('foo')

    def test_init(self):
        root = '/foo/bar/'
        url = 'https://example.com'

        # Test default
        cache = HashFileCache(root, url)
        self.assertEqual(cache.root, root)
        self.assertEqual(cache.url, url)
        self.assertFalse(cache.gzip)

        # Test setting gzip
        cache = HashFileCache(root, url, gzip=True)
        self.assertEqual(cache.root, root)
        self.assertEqual(cache.url, url)
        self.assertTrue(cache.gzip)

    def test_create_error(self):
        with self.assertRaises(NotADirectoryError):
            cache = HashFileCache('/', '')
            cache.create('/dev/null/reee')

    def test_has_file(self):
        self.assertFalse(self.cache.has_file('random', 'bar'))
        with tempfile.NamedTemporaryFile(dir=os.path.join(self.temp_dir, 'foo')) as f:
            fname = f.name
            self.assertTrue(self.cache.has_file('foo', fname))
        self.assertFalse(self.cache.has_file('foo', fname))

    def test_get_path(self):
        self.assertTrue(self.cache.get_path('foo', 'bar'), os.path.join(self.temp_dir, 'foo', 'bar'))
        self.assertTrue(self.cache.get_path('bar', 'foo'), os.path.join(self.temp_dir, 'bar', 'foo'))

    def test_get_url(self):
        urls = [
            ('foo', 'bar'),
            ('foo/', 'bar/'),
            ('/foo', '/bar'),
            ('foo/', '/bar'),
            ('/foo', 'bar/'),
            ('/foo', '/bar/'),
        ]
        for hash, file in urls:
            self.assertTrue(self.cache.get_url(hash, file), urljoin(self.cache.url, '%s/%s' % (hash, file)))

    def test_read_file(self):
        # The directory removal in tear down will clean up this file, so we don't have to cleanup here
        with tempfile.NamedTemporaryFile(dir=os.path.join(self.temp_dir, 'foo'), delete=False) as f:
            fname = f.name
            f.write(b'bar')
        with self.cache.read_file('foo', fname) as cache_f:
            self.assertTrue(cache_f.read(), b'bar')
            with self.assertRaises(UnsupportedOperation):
                cache_f.write(b'write')

    def test_read_data(self):
        # The directory removal in tear down will clean up this file, so we don't have to cleanup here
        with tempfile.NamedTemporaryFile(dir=os.path.join(self.temp_dir, 'foo'), delete=False) as f:
            fname = f.name
            f.write(b'bar')
        self.assertEqual(self.cache.read_data('foo', fname), b'bar')

    def test_cache_data_normal(self):
        self.assertIsNone(self.cache.cache_data('foo', 'a', b'bar', url=False, gzip=False))
        self.assertEqual(self.cache.read_data('foo', 'a'), b'bar')
        self.assertEqual(
            self.cache.cache_data('foo', 'b', b'bar', url=True, gzip=False),
            self.cache.get_url('foo', 'b')
        )

    def test_cache_data_gzip(self):
        self.assertIsNone(self.gzip_cache.cache_data('foo', 'a', b'bar', url=False))
        self.assertEqual(self.gzip_cache.read_data('foo', 'a'), b'bar')
        self.assertEqual(
            self.gzip_cache.cache_data('foo', 'b', b'bar', url=True, gzip=True),
            self.cache.get_url('foo', 'b')
        )

        # Test that these files are actually gzip files
        with gzip.open(self.gzip_cache.get_path('foo', 'a.gz'), 'rb') as f:
            f.read()
        with gzip.open(self.gzip_cache.get_path('foo', 'b.gz'), 'rb') as f:
            f.read()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.gzip_temp_dir)
