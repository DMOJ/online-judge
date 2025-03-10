from django.core.cache import cache
from django.test import SimpleTestCase

from judge.utils.opengraph import generate_opengraph


HTML = '''
%s

![Alt text](https://example.com/image.png)
''' % ('word\\\\(\\\\)\\\\[\\\\] ' * 50)  # Make sure literal backslashes followed by brackets are removed

TRUNCATE_HTML = '''
# Header
![Alt text](https://example.com/image.png)

%s

[A random link](https://example.com/)

Another paragraph that won't be used in the description
![Alt text 2](https://example.com/image2.png)
''' % ('word ' * 80)

NO_DESCRIPTION_HTML = '![Alt text](https://example.com/image.png)'

BLANK_HTML = ''


class OpengraphTestCase(SimpleTestCase):
    def setUp(self):
        # Django doesn't setup a test cache (yet*) so we make sure to clear it here.
        # [*] https://docs.djangoproject.com/en/3.0/topics/testing/overview/#other-test-conditions
        cache.delete('foo')

    def test_opengraph_cache(self):
        with self.assertRaises(TypeError):
            generate_opengraph('foo', None, None)
        cache.set('foo', True, 1000)
        # This would through a TypeError if it wasn't directly taken from the cache
        self.assertTrue(generate_opengraph('foo', None, None))

    def test_generaete_opengraph(self):
        self.assertEqual(
            generate_opengraph('foo', HTML, style=None),
            (('word ' * 50).strip(), 'https://example.com/image.png'),
        )
        cache.delete('foo')
        self.assertEqual(
            generate_opengraph('foo', TRUNCATE_HTML, style=None),
            ('%s…' % ('word ' * 60), 'https://example.com/image.png'),
        )
        cache.delete('foo')
        self.assertEqual(
            generate_opengraph('foo', NO_DESCRIPTION_HTML, style=None),
            ('None', 'https://example.com/image.png'),
        )
        cache.delete('foo')
        self.assertEqual(
            generate_opengraph('foo', BLANK_HTML, style=None),
            ('None', None),
        )

    def tearDown(self):
        # We'll clean up the cache again for future use.
        cache.delete('foo')
