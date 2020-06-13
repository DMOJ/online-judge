import base64
import hmac
import struct

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from django.utils.encoding import force_bytes

from judge.models import Profile
from judge.models.tests.util import CommonDataMixin, create_contest, create_contest_participation


class OrganizationTestCase(CommonDataMixin, TestCase):
    @classmethod
    def setUpTestData(self):
        super().setUpTestData()
        self.profile = self.users['normal'].profile
        self.profile.organizations.add(self.organizations['open'])

    def test_contains(self):
        self.assertIn(self.profile, self.organizations['open'])
        self.assertIn(self.profile.id, self.organizations['open'])

        self.assertNotIn(self.users['superuser'].profile, self.organizations['open'])
        self.assertNotIn(self.users['superuser'].profile.id, self.organizations['open'])

        with self.assertRaisesRegex(TypeError, 'Organization membership test'):
            'aaaa' in self.organizations['open']

    def test_str(self):
        self.assertEqual(str(self.organizations['open']), 'open')


class ProfileTestCase(CommonDataMixin, TestCase):
    @classmethod
    def setUpTestData(self):
        super().setUpTestData()
        self.profile = self.users['normal'].profile
        self.profile.organizations.add(self.organizations['open'])

    def setUp(self):
        # We are doing a LOT of field modifications in this test case.
        # This is to prevent cryptic error messages when a test fails due
        # to modifications in another test. In theory, no two tests should
        # touch the same field, but who knows.
        self.profile.refresh_from_db()

    def test_username(self):
        self.assertEqual(str(self.profile), self.profile.username)

    def test_organization(self):
        self.assertIsNone(self.users['superuser'].profile.organization)
        self.assertEqual(self.profile.organization, self.organizations['open'])

    def test_calculate_points(self):
        self.profile.calculate_points()

        # Test saving
        for attr in ('points', 'problem_count', 'performance_points'):
            with self.subTest(attribute=attr):
                setattr(self.profile, attr, -1000)
                self.assertEqual(getattr(self.profile, attr), -1000)
                self.profile.calculate_points()
                self.assertEqual(getattr(self.profile, attr), 0)

    def test_generate_api_token(self):
        token = self.profile.generate_api_token()

        self.assertIsInstance(token, str)
        self.assertIsInstance(self.profile.api_token, str)

        user_id, raw_token = struct.unpack('>I32s', base64.urlsafe_b64decode(token))

        self.assertEqual(self.users['normal'].id, user_id)
        self.assertEqual(len(raw_token), 32)

        self.assertTrue(
            hmac.compare_digest(
                hmac.new(force_bytes(settings.SECRET_KEY), msg=force_bytes(raw_token), digestmod='sha256').hexdigest(),
                self.profile.api_token,
            ),
        )

    def test_update_contest(self):
        _now = timezone.now()
        for contest in (
            create_contest(
                key='finished_contest',
                start_time=_now - timezone.timedelta(days=100),
                end_time=_now - timezone.timedelta(days=10),
                is_visible=True,
            ),
            create_contest(
                key='inaccessible_contest',
                start_time=_now - timezone.timedelta(days=100),
                end_time=_now + timezone.timedelta(days=10),
            ),
        ):
            with self.subTest(name=contest.name):
                self.profile.current_contest = create_contest_participation(
                    contest=contest,
                    user=self.profile,
                )
                self.assertIsNotNone(self.profile.current_contest)
                self.profile.update_contest()
                self.assertIsNone(self.profile.current_contest)

    def test_css_class(self):
        self.assertEqual(self.profile.css_class, 'rating rate-none user')

    def test_get_user_css_class(self):
        self.assertEqual(
            Profile.get_user_css_class(display_rank='abcdef', rating=None, rating_colors=True),
            'rating rate-none abcdef',
        )
        self.assertEqual(
            Profile.get_user_css_class(display_rank='admin', rating=1200, rating_colors=True),
            'rating rate-expert admin',
        )
        self.assertEqual(
            Profile.get_user_css_class(display_rank=1111, rating=1199, rating_colors=True),
            'rating rate-amateur 1111',
        )
        self.assertEqual(
            Profile.get_user_css_class(display_rank='random', rating=1199, rating_colors=False),
            'random',
        )
