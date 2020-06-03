from django.test import SimpleTestCase

from . import markdown


class TestMarkdown(SimpleTestCase):
    BLEACHED_STYLE = 'problem'
    UNBLEACHED_STYLE = 'problem-full'

    def test_bleach(self):
        self.assertEqual(markdown('<script>void(0)</script>', self.BLEACHED_STYLE),
                         '&lt;script&gt;void(0)&lt;/script&gt;')

    def test_no_bleach(self):
        self.assertEqual(markdown('<script>void(0)</script>', self.UNBLEACHED_STYLE),
                         '<script>void(0)</script>')
