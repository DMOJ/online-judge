from django.test import SimpleTestCase

from judge.utils.unicode import utf8bytes, utf8text


class UnicodeTestCase(SimpleTestCase):
    def test_utf8_bytes(self):
        self.assertEqual(utf8bytes(None), None)
        self.assertEqual(utf8bytes(b''), b'')
        self.assertEqual(utf8bytes(b'test'), b'test')
        self.assertEqual(utf8bytes(b'\xc2\xbc\xc2\xbd\xc2\xbe'), b'\xc2\xbc\xc2\xbd\xc2\xbe')
        self.assertEqual(utf8bytes(''), b'')
        self.assertEqual(utf8bytes('test'), b'test')
        self.assertEqual(utf8bytes('\xbc\xbd\xbe'), b'\xc2\xbc\xc2\xbd\xc2\xbe')
        with self.assertRaises(AttributeError):
            utf8bytes(15)
        with self.assertRaises(AttributeError):
            utf8bytes(True)

    def test_utf8_text(self):
        self.assertEqual(utf8text(None), None)
        self.assertEqual(utf8text(b''), '')
        self.assertEqual(utf8text(b'test'), 'test')
        self.assertEqual(utf8text(b'\xc2\xbc\xc2\xbd\xc2\xbe'), '\xbc\xbd\xbe')
        self.assertEqual(utf8text(''), '')
        self.assertEqual(utf8text('test'), 'test')
        self.assertEqual(utf8text('\xbc\xbd\xbe'), '\xbc\xbd\xbe')
        with self.assertRaises(AttributeError):
            utf8text(15)
        with self.assertRaises(AttributeError):
            utf8text(True)
        with self.assertRaisesRegex(UnicodeDecodeError, 'invalid start byte'):
            utf8text('\xff'.encode('utf-16'))
        self.assertEquals(utf8text('\xff'.encode('utf-16'), errors='replace'),
                          b'\xef\xbf\xbd\xef\xbf\xbd\xef\xbf\xbd\x00'.decode())
        utf8text('\xff\xff'.encode('utf-16'), errors='ignore')
