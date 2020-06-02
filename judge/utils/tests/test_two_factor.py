from django.test import SimpleTestCase

from judge.utils.two_factor import webauthn_decode, webauthn_encode


class TwoFactorTestCase(SimpleTestCase):
    def test_webauthn_decode(self):
        self.assertEqual(webauthn_decode(''), b'')
        self.assertEqual(webauthn_decode('AA'), bytes(range(1)))
        self.assertEqual(webauthn_decode('AAE'), bytes(range(2)))
        self.assertEqual(webauthn_decode('f39_'), b'\x7f\x7f\x7f')
        self.assertEqual(webauthn_decode(
            'AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0-Pw'), bytes(range(64)))

    def test_webauthn_encode(self):
        self.assertEqual(webauthn_encode(b''), '')
        self.assertEqual(webauthn_encode(bytes(range(1))), 'AA')
        self.assertEqual(webauthn_encode(bytes(range(2))), 'AAE')
        self.assertEqual(webauthn_encode(b'\x7f\x7f\x7f'), 'f39_')
        self.assertEqual(webauthn_encode(bytes(range(64))),
                         'AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0-Pw')
