from django.test import SimpleTestCase

from judge.utils.strings import safe_int_or_none, safe_float_or_none


class StringsTestCase(SimpleTestCase):
    def test_safe_int_or_none(self):
        self.assertEquals(safe_int_or_none(10), 10)
        self.assertEquals(safe_int_or_none('10'), 10)
        self.assertEquals(safe_int_or_none(True), 1)
        self.assertEquals(safe_int_or_none(False), 0)
        self.assertEquals(safe_int_or_none(None), None)
        self.assertEquals(safe_int_or_none([]), None)
        self.assertEquals(safe_int_or_none({}), None)
        self.assertEquals(safe_int_or_none('test'), None)
        self.assertEquals(safe_int_or_none('10.0'), None)

    def test_safe_float_or_none(self):
        self.assertEquals(safe_float_or_none(10), 10)
        self.assertEquals(safe_float_or_none('10'), 10)
        self.assertEquals(safe_float_or_none('10.0'), 10.0)
        self.assertEquals(safe_float_or_none(True), 1)
        self.assertEquals(safe_float_or_none(False), 0)
        self.assertEquals(safe_float_or_none(None), None)
        self.assertEquals(safe_float_or_none([]), None)
        self.assertEquals(safe_float_or_none({}), None)
        self.assertEquals(safe_float_or_none('test'), None)
