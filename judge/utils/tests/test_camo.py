import hmac
from hashlib import sha1

from django.test import SimpleTestCase
from lxml.html import HTMLParser, fromstring, tostring

from judge.utils.camo import CamoClient
from judge.utils.unicode import utf8bytes


# TODO: Test the setting of judge.utils.camo.client depending on settings variables. I've tried my hardest... but the
#       settings just don't get set so client is always None.
class CamoClientTestCase(SimpleTestCase):
    def setUp(self):
        self.example_url = '//example.com'
        self.example_url_http = 'http:%s' % self.example_url
        self.example_url_https = 'https:%s' % self.example_url
        self.test_url = '//test.test/img.png/'
        self.test_url_http = 'http:%s' % self.test_url
        self.test_url_https = 'https:%s' % self.test_url

        self.http_camo = CamoClient(self.example_url_http, 'key', excluded=('https://github.com/',))
        self.https_camo = CamoClient(self.example_url_https, 'key', https=True)

        # These urls are generated the same way camo does
        self.camo_blank_url = '%s/%s/' % (
            self.http_camo.server,
            hmac.new(utf8bytes(''), utf8bytes(''), sha1).hexdigest(),
        )
        self.camo_image_url = '%s/%s/%s' % (
            self.http_camo.server,
            hmac.new(utf8bytes('key'), utf8bytes(self.test_url_http), sha1).hexdigest(),
            utf8bytes(self.test_url_http).hex(),
        )

    def test_removing_trailing_slash(self):
        self.assertEqual(self.http_camo.server, self.example_url_http)

    def test_image_url(self):
        self.assertEqual(CamoClient(self.example_url_http, '').image_url(''), self.camo_blank_url)
        self.assertEqual(self.http_camo.image_url(self.test_url_http), self.camo_image_url)

    def test_rewrite(self):
        self.assertEqual(self.http_camo.rewrite_url(self.http_camo.server), self.http_camo.server)
        self.assertEqual(self.http_camo.rewrite_url(self.http_camo.excluded[0]), self.http_camo.excluded[0])
        self.assertEqual(self.http_camo.rewrite_url(self.test_url_http), self.camo_image_url)
        self.assertEqual(self.http_camo.rewrite_url(self.test_url_https), self.http_camo.image_url(self.test_url_https))
        self.assertEqual(self.http_camo.rewrite_url(self.example_url), self.example_url_http)
        self.assertEqual(self.https_camo.rewrite_url(self.example_url), self.example_url_https)
        self.assertEqual(self.http_camo.rewrite_url(self.test_url), self.camo_image_url)
        self.assertEqual(self.https_camo.rewrite_url(self.test_url), self.https_camo.image_url(self.test_url_https))
        self.assertEqual(self.http_camo.rewrite_url('wss://other.test'), 'wss://other.test')

    def test_update_tree(self):
        base = '<html><body>%s</body></html>'
        update_elements = (
            base % '<img src="{0}">',
            base % '<img data-src="{0}">',
            base % '<img src="{0}" data-src="{0}">',
            base % '<img src="{0}" class="additional">',
            base % '<object data="{0}"></object>',
        )
        ignore_elements = (
            base % '<link src="{0}">',
            base % '<script src="{0}">',
            base % '<a href="{0}">',
            base % '<video data-src="{0}">',
        )
        urls = (
            self.example_url,
            self.example_url_http,
            self.example_url_https,
            self.http_camo.excluded[0],
            self.test_url,
            self.test_url_http,
            self.test_url_https,
        )
        for camo in (self.http_camo, self.https_camo):
            # Test that every element that's supposed to get updated is updated to the rewritten element
            for element in update_elements:
                for url in urls:
                    html = fromstring(element.format(url), parser=HTMLParser())
                    camo.update_tree(html)
                    self.assertEqual(tostring(html, encoding='unicode'), element.format(camo.rewrite_url(url)))

            # Test that other elements are left untouched
            for element in ignore_elements:
                for url in urls:
                    html_orig = fromstring(element.format(url), parser=HTMLParser())
                    html = html_orig
                    camo.update_tree(html)
                    self.assertEqual(html, html_orig)
