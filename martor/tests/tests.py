
from django.test import TestCase


class SimpleTest(TestCase):

    def test_me(self):
        response = self.client.get('/test-form-view/')
        self.assertEqual(response.status_code, 200)
