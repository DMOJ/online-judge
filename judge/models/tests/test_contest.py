from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from judge.models import Contest, ContestParticipation, ContestTag
from judge.models.contest import MinValueOrNoneValidator
from judge.models.tests.util import CommonDataMixin, create_contest, create_contest_participation, create_user


class ContestTestCase(CommonDataMixin, TestCase):
    @classmethod
    def setUpTestData(self):
        super().setUpTestData()
        self.users.update({
            'staff_contest_edit_own': create_user(
                username='staff_contest_edit_own',
                is_staff=True,
                user_permissions=('edit_own_contest',),
            ),
            'staff_contest_see_all': create_user(
                username='staff_contest_see_all',
                user_permissions=('see_private_contest',),
            ),
            'staff_contest_edit_all': create_user(
                username='staff_contest_edit_all',
                is_staff=True,
                user_permissions=('edit_own_contest', 'edit_all_contest'),
            ),
        })

        _now = timezone.now()

        self.basic_contest = create_contest(
            key='basic',
            start_time=_now - timezone.timedelta(days=1),
            end_time=_now + timezone.timedelta(days=100),
            organizers=('superuser', 'staff_contest_edit_own'),
        )

        self.hidden_scoreboard_contest = create_contest(
            key='hidden_scoreboard',
            start_time=_now - timezone.timedelta(days=1),
            end_time=_now + timezone.timedelta(days=100),
            is_visible=True,
            hide_scoreboard=True,
            problem_label_script='''
                function(n)
                    return tostring(math.floor(n))
                end
            ''',
        )

        self.users['normal'].profile.current_contest = create_contest_participation(
            contest='hidden_scoreboard',
            user='normal',
        )
        self.users['normal'].profile.save()

        self.hidden_scoreboard_contest.update_user_count()

        self.private_contest = create_contest(
            key='private',
            start_time=_now - timezone.timedelta(days=5),
            end_time=_now - timezone.timedelta(days=3),
            is_visible=True,
            is_private=True,
            is_organization_private=True,
            private_contestants=('staff_contest_edit_own',),
        )

        self.organization_private_contest = create_contest(
            key='organization_private',
            start_time=_now + timezone.timedelta(days=3),
            end_time=_now + timezone.timedelta(days=6),
            is_visible=True,
            is_organization_private=True,
            organizations=('open',),
            view_contest_scoreboard=('normal',),
        )

        self.private_user_contest = create_contest(
            key='private_user',
            start_time=_now - timezone.timedelta(days=3),
            end_time=_now + timezone.timedelta(days=6),
            is_visible=True,
            is_private=True,
        )

    def setUp(self):
        self.users['normal'].profile.refresh_from_db()

    def test_basic_contest(self):
        self.assertTrue(self.basic_contest.show_scoreboard)
        self.assertEqual(self.basic_contest.contest_window_length, timezone.timedelta(days=101))
        self.assertIsInstance(self.basic_contest._now, timezone.datetime)
        self.assertTrue(self.basic_contest.can_join)
        self.assertIsNone(self.basic_contest.time_before_start)
        self.assertIsInstance(self.basic_contest.time_before_end, timezone.timedelta)
        self.assertFalse(self.basic_contest.ended)
        self.assertEqual(str(self.basic_contest), self.basic_contest.name)
        self.assertEqual(self.basic_contest.get_label_for_problem(0), '1')

    def test_hidden_scoreboard_contest(self):
        self.assertFalse(self.hidden_scoreboard_contest.show_scoreboard)
        for i in range(3):
            with self.subTest(contest_problem_index=i):
                self.assertEqual(self.hidden_scoreboard_contest.get_label_for_problem(i), str(i))
        self.assertEqual(self.hidden_scoreboard_contest.user_count, 1)

    def test_private_contest(self):
        self.assertTrue(self.private_contest.can_join)
        self.assertIsNone(self.private_contest.time_before_start)
        self.assertIsNone(self.private_contest.time_before_end)

    def test_organization_private_contest(self):
        self.assertFalse(self.organization_private_contest.can_join)
        self.assertFalse(self.organization_private_contest.show_scoreboard)
        self.assertFalse(self.organization_private_contest.ended)
        self.assertIsInstance(self.organization_private_contest.time_before_start, timezone.timedelta)
        self.assertIsInstance(self.organization_private_contest.time_before_end, timezone.timedelta)

    def test_basic_contest_methods(self):
        with self.assertRaises(Contest.Inaccessible):
            self.basic_contest.access_check(self.users['normal'])

        data = {
            'superuser': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
                'is_in_contest': self.assertFalse,
            },
            'staff_contest_edit_own': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
                'is_in_contest': self.assertFalse,
            },
            'staff_contest_see_all': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
            'staff_contest_edit_all': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
                'is_in_contest': self.assertFalse,
            },
            'normal': {
                # scoreboard checks don't do accessibility checks
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
            'anonymous': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.basic_contest, data)

    def test_hidden_scoreboard_contest_methods(self):
        data = {
            'staff_contest_edit_own': {
                'can_see_own_scoreboard': self.assertFalse,
                'can_see_full_scoreboard': self.assertFalse,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
            'staff_contest_see_all': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
            'staff_contest_edit_all': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
                'is_in_contest': self.assertFalse,
            },
            'normal': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertFalse,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertTrue,
            },
            'anonymous': {
                'can_see_own_scoreboard': self.assertFalse,
                'can_see_full_scoreboard': self.assertFalse,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.hidden_scoreboard_contest, data)

    def test_private_contest_methods(self):
        with self.assertRaises(Contest.PrivateContest):
            self.private_contest.access_check(self.users['normal'])
        self.private_contest.private_contestants.add(self.users['normal'].profile)
        with self.assertRaises(Contest.PrivateContest):
            self.private_contest.access_check(self.users['normal'])
        self.private_contest.organizations.add(self.organizations['open'])
        self.users['normal'].profile.organizations.add(self.organizations['open'])

        data = {
            'normal': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
            'staff_contest_see_all': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
            'anonymous': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.private_contest, data)

    def test_organization_private_contest_methods(self):
        data = {
            'staff_contest_edit_own': {
                'can_see_own_scoreboard': self.assertFalse,
                'can_see_full_scoreboard': self.assertFalse,
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
            'staff_contest_see_all': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
            'staff_contest_edit_all': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
                'is_in_contest': self.assertFalse,
            },
            'normal': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
            'anonymous': {
                # False because contest has not begun
                'can_see_own_scoreboard': self.assertFalse,
                'can_see_full_scoreboard': self.assertFalse,
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.organization_private_contest, data)

    def test_private_user_contest_methods(self):
        data = {
            'superuser': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
                'is_in_contest': self.assertFalse,
            },
            'normal': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
            'anonymous': {
                'can_see_own_scoreboard': self.assertTrue,
                'can_see_full_scoreboard': self.assertTrue,
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
                'is_in_contest': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.private_user_contest, data)

    def test_contests_list(self):
        for name, user in self.users.items():
            with self.subTest(user=name):
                # We only care about consistency between Contest.is_accessible_by and Contest.get_visible_contests
                contest_keys = []
                for contest in Contest.objects.prefetch_related('organizers', 'private_contestants', 'organizations'):
                    if contest.is_accessible_by(user):
                        contest_keys.append(contest.key)

                self.assertCountEqual(
                    Contest.get_visible_contests(user).values_list('key', flat=True),
                    contest_keys,
                )

    def test_contest_clean(self):
        _now = timezone.now()
        contest = create_contest(
            key='contest',
            start_time=_now,
            end_time=_now - timezone.timedelta(days=1),
            problem_label_script='invalid',
            format_config={'invalid': 'invalid'},
        )
        with self.assertRaisesRegex(ValidationError, 'ended before it starts'):
            contest.full_clean()
        contest.end_time = _now
        with self.assertRaisesRegex(ValidationError, 'ended before it starts'):
            contest.full_clean()
        contest.end_time = _now + timezone.timedelta(days=1)
        with self.assertRaisesRegex(ValidationError, 'default contest expects'):
            contest.full_clean()
        contest.format_config = {}
        with self.assertRaisesRegex(ValidationError, 'Contest problem label script'):
            contest.full_clean()
        contest.problem_label_script = '''
            function(n)
                return n
            end
        '''
        # Test for bad problem label script caching
        with self.assertRaisesRegex(ValidationError, 'Contest problem label script'):
            contest.full_clean()
        del contest.get_label_for_problem
        with self.assertRaisesRegex(ValidationError, 'should return a string'):
            contest.full_clean()
        contest.problem_label_script = ''
        del contest.get_label_for_problem
        contest.full_clean()

    def test_normal_user_current_contest(self):
        current_contest = self.users['normal'].profile.current_contest
        self.assertIsNotNone(current_contest)

        current_contest.set_disqualified(True)
        self.users['normal'].profile.refresh_from_db()
        self.assertTrue(current_contest.is_disqualified)
        self.assertIsNone(self.users['normal'].profile.current_contest)
        self.assertEqual(current_contest.score, -9999)

        current_contest.set_disqualified(False)
        self.users['normal'].profile.refresh_from_db()
        self.assertFalse(current_contest.is_disqualified)
        self.assertIsNone(self.users['normal'].profile.current_contest)
        self.assertEqual(current_contest.score, 0)

    def test_live_participation(self):
        participation = ContestParticipation.objects.get(
            contest=self.hidden_scoreboard_contest,
            user=self.users['normal'].profile,
            virtual=ContestParticipation.LIVE,
        )
        self.assertTrue(participation.live)
        self.assertFalse(participation.spectate)
        self.assertEqual(participation.end_time, participation.contest.end_time)
        self.assertFalse(participation.ended)
        self.assertIsInstance(participation.time_remaining, timezone.timedelta)

    def test_spectating_participation(self):
        participation = create_contest_participation(
            contest='hidden_scoreboard',
            user='superuser',
            virtual=ContestParticipation.SPECTATE,
        )

        self.assertFalse(participation.live)
        self.assertTrue(participation.spectate)
        self.assertEqual(participation.start, participation.contest.start_time)
        self.assertEqual(participation.end_time, participation.contest.end_time)

    def test_virtual_participation(self):
        participation = create_contest_participation(
            contest='private',
            user='superuser',
            virtual=1,
        )

        self.assertFalse(participation.live)
        self.assertFalse(participation.spectate)
        self.assertEqual(participation.start, participation.real_start)
        self.assertIsInstance(participation.end_time, timezone.datetime)


class ContestTagTestCase(TestCase):
    @classmethod
    def setUpTestData(self):
        self.basic_tag = ContestTag.objects.create(
            name='basic',
            color='#fff',
        )
        self.dark_tag = ContestTag.objects.create(
            name='dark',
            color='#010001',
        )

    def test_basic_tag(self):
        self.assertEqual(str(self.basic_tag), self.basic_tag.name)
        self.assertEqual(self.basic_tag.text_color, '#000')

    def test_dark_tag(self):
        self.assertEqual(self.dark_tag.text_color, '#fff')


class MinValueOrNoneValidatorTestCase(SimpleTestCase):
    def test_both_integers(self):
        self.assertIsNone(MinValueOrNoneValidator(-1)(100))
        self.assertIsNone(MinValueOrNoneValidator(0)(0))
        self.assertIsNone(MinValueOrNoneValidator(100)(100))

    def test_integer_bound_none_value(self):
        self.assertIsNone(MinValueOrNoneValidator(-100)(None))
        self.assertIsNone(MinValueOrNoneValidator(0)(None))
        self.assertIsNone(MinValueOrNoneValidator(100)(None))

    def test_none_bound_integer_value(self):
        self.assertIsNone(MinValueOrNoneValidator(None)(-100))
        self.assertIsNone(MinValueOrNoneValidator(None)(0))
        self.assertIsNone(MinValueOrNoneValidator(None)(100))

    def test_both_none(self):
        self.assertIsNone(MinValueOrNoneValidator(None)(None))

    def test_fail(self):
        with self.assertRaises(ValidationError):
            MinValueOrNoneValidator(0)(-1)

        with self.assertRaises(ValidationError):
            MinValueOrNoneValidator(100)(0)
