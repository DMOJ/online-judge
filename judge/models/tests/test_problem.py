from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from judge.models import Language, LanguageLimit, Problem
from judge.models.problem import disallowed_characters_validator
from judge.models.tests.util import CommonDataMixin, create_organization, create_problem, create_problem_type, \
    create_solution, create_user


class ProblemTestCase(CommonDataMixin, TestCase):
    @classmethod
    def setUpTestData(self):
        super().setUpTestData()

        self.users.update({
            'staff_problem_edit_only_all': create_user(
                username='staff_problem_edit_only_all',
                is_staff=True,
                user_permissions=('edit_all_problem',),
            ),
        })

        create_problem_type(name='type')

        self.basic_problem = create_problem(
            code='basic',
            allowed_languages=Language.objects.values_list('key', flat=True),
            types=('type',),
            authors=('normal',),
            testers=('staff_problem_edit_public',),
        )

        limits = []
        for lang in Language.objects.filter(common_name=Language.get_python3().common_name):
            limits.append(
                LanguageLimit(
                    problem=self.basic_problem,
                    language=lang,
                    time_limit=100,
                    memory_limit=131072,
                ),
            )
        LanguageLimit.objects.bulk_create(limits)

        self.organization_private_problem = create_problem(
            code='organization_private',
            time_limit=2,
            is_public=True,
            is_organization_private=True,
            curators=('staff_problem_edit_own', 'staff_problem_edit_own_no_staff'),
        )

        self.problem_organization = create_organization(
            name='problem organization',
            admins=('normal', 'staff_problem_edit_public'),
        )
        self.organization_admin_private_problem = create_problem(
            code='org_admin_private',
            is_organization_private=True,
            organizations=('problem organization',),
        )
        self.organization_admin_problem = create_problem(
            code='organization_admin',
            organizations=('problem organization',),
        )

    def test_basic_problem(self):
        self.assertEqual(str(self.basic_problem), self.basic_problem.name)
        self.assertCountEqual(
            self.basic_problem.languages_list(),
            set(Language.objects.values_list('common_name', flat=True)),
        )
        self.basic_problem.user_count = -1000
        self.basic_problem.ac_rate = -1000
        self.basic_problem.update_stats()
        self.assertEqual(self.basic_problem.user_count, 0)
        self.assertEqual(self.basic_problem.ac_rate, 0)

        self.assertListEqual(list(self.basic_problem.author_ids), [self.users['normal'].profile.id])
        self.assertListEqual(list(self.basic_problem.editor_ids), [self.users['normal'].profile.id])
        self.assertListEqual(list(self.basic_problem.tester_ids), [self.users['staff_problem_edit_public'].profile.id])
        self.assertListEqual(list(self.basic_problem.usable_languages), [])
        self.assertListEqual(self.basic_problem.types_list, ['type'])
        self.assertSetEqual(self.basic_problem.usable_common_names, set())

        self.assertEqual(self.basic_problem.translated_name('ABCDEFGHIJK'), self.basic_problem.name)

        self.assertFalse(self.basic_problem.clarifications.exists())

    def test_basic_problem_language_limits(self):
        for common_name, memory_limit in self.basic_problem.language_memory_limit:
            self.assertEqual(memory_limit, 131072)
        for common_name, time_limit in self.basic_problem.language_time_limit:
            self.assertEqual(time_limit, 100)

    def test_basic_problem_methods(self):
        self.assertTrue(self.basic_problem.is_editor(self.users['normal'].profile))

        data = {
            'superuser': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'staff_problem_edit_own': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
            'staff_problem_see_all': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
            },
            'staff_problem_edit_all': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'staff_problem_edit_public': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
            },
            'staff_problem_see_organization': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
            'normal': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
            },
            'anonymous': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.basic_problem, data)

    def test_organization_private_problem_methods(self):
        self.assertFalse(self.organization_private_problem.is_accessible_by(self.users['normal']))
        self.users['normal'].profile.organizations.add(self.organizations['open'])
        self.assertFalse(self.organization_private_problem.is_accessible_by(self.users['normal']))
        self.organization_private_problem.organizations.add(self.organizations['open'])

        data = {
            'staff_problem_edit_own': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
                'is_subs_manageable_by': self.assertTrue,
            },
            'staff_problem_see_all': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_subs_manageable_by': self.assertFalse,
            },
            'staff_problem_edit_all': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'staff_problem_edit_public': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'staff_problem_see_organization': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
            },
            'staff_problem_edit_all_with_rejudge': {
                'is_editable_by': self.assertTrue,
                'is_subs_manageable_by': self.assertTrue,
            },
            'staff_problem_edit_own_no_staff': {
                'is_editable_by': self.assertTrue,
                'is_subs_manageable_by': self.assertFalse,
            },
            'normal': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
            },
            'anonymous': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.organization_private_problem, data)

    def test_organization_admin_private_problem_methods(self):
        data = {
            'staff_problem_edit_own': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
                'is_subs_manageable_by': self.assertFalse,
            },
            'staff_problem_see_all': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertFalse,
                'is_subs_manageable_by': self.assertFalse,
            },
            'staff_problem_edit_all': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'staff_problem_edit_public': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'staff_problem_see_organization': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
            'staff_organization_admin': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
            'normal': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
            'anonymous': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.organization_admin_private_problem, data)

    def test_organization_admin_problem_methods(self):
        data = {
            'staff_problem_edit_all': {
                'is_accessible_by': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'staff_problem_edit_public': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
            'staff_organization_admin': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
            'normal': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
            'anonymous': {
                'is_accessible_by': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.organization_admin_problem, data)

    def test_problems_list(self):
        for name, user in self.users.items():
            with self.subTest(user=name):
                with self.subTest(list='accessible problems'):
                    # We only care about consistency between Problem.is_accessible_by and Problem.get_visible_problems
                    problem_codes = []
                    for problem in Problem.objects.prefetch_related('authors', 'curators', 'testers', 'organizations'):
                        if problem.is_accessible_by(user):
                            problem_codes.append(problem.code)

                    self.assertCountEqual(
                        Problem.get_visible_problems(user).distinct().values_list('code', flat=True),
                        problem_codes,
                    )

                with self.subTest(list='editable problems'):
                    # We only care about consistency between Problem.is_editable_by and Problem.get_editable_problems
                    problem_codes = []
                    for problem in Problem.objects.prefetch_related('authors', 'curators'):
                        if problem.is_editable_by(user):
                            problem_codes.append(problem.code)

                    self.assertCountEqual(
                        Problem.get_editable_problems(user).distinct().values_list('code', flat=True),
                        problem_codes,
                    )


class SolutionTestCase(CommonDataMixin, TestCase):
    @classmethod
    def setUpTestData(self):
        super().setUpTestData()
        self.users.update({
            'staff_solution_see_all': create_user(
                username='staff_solution_see_all',
                user_permissions=('see_private_solution',),
            ),
        })

        _now = timezone.now()

        self.basic_solution = create_solution(problem='basic')

        self.private_solution = create_solution(
            problem='private',
            is_public=False,
            publish_on=_now - timezone.timedelta(days=100),
        )

        self.unpublished_problem = create_problem(
            code='unpublished',
            name='Unpublished',
            authors=('staff_problem_edit_own',),
        )
        self.unpublished_solution = create_solution(
            problem=self.unpublished_problem,
            is_public=False,
            publish_on=_now + timezone.timedelta(days=100),
            authors=('normal',),
        )

    def test_unpublished_solution(self):
        self.assertEqual(str(self.unpublished_solution), 'Editorial for Unpublished')

    def test_basic_solution_methods(self):
        data = {
            'superuser': {
                'is_accessible_by': self.assertTrue,
            },
            'staff_solution_see_all': {
                'is_accessible_by': self.assertTrue,
            },
            'normal': {
                'is_accessible_by': self.assertTrue,
            },
            'anonymous': {
                'is_accessible_by': self.assertTrue,
            },
        }
        self._test_object_methods_with_users(self.basic_solution, data)

    def test_private_solution_methods(self):
        data = {
            'superuser': {
                'is_accessible_by': self.assertTrue,
            },
            'staff_solution_see_all': {
                'is_accessible_by': self.assertTrue,
            },
            'staff_problem_edit_own': {
                'is_accessible_by': self.assertFalse,
            },
            'staff_problem_see_all': {
                'is_accessible_by': self.assertFalse,
            },
            'staff_problem_edit_all': {
                'is_accessible_by': self.assertTrue,
            },
            'staff_problem_edit_public': {
                'is_accessible_by': self.assertFalse,
            },
            'normal': {
                'is_accessible_by': self.assertFalse,
            },
            'anonymous': {
                'is_accessible_by': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.private_solution, data)

    def test_unpublished_solution_methods(self):
        data = {
            'staff_solution_see_all': {
                'is_accessible_by': self.assertTrue,
            },
            'staff_problem_edit_own': {
                'is_accessible_by': self.assertTrue,
            },
            'staff_problem_edit_all': {
                'is_accessible_by': self.assertTrue,
            },
            'staff_problem_edit_public': {
                'is_accessible_by': self.assertFalse,
            },
            'normal': {
                'is_accessible_by': self.assertFalse,
            },
            'anonymous': {
                'is_accessible_by': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.unpublished_solution, data)


class DisallowedCharactersValidatorTestCase(SimpleTestCase):
    def test_valid(self):
        with self.settings(DMOJ_PROBLEM_STATEMENT_DISALLOWED_CHARACTERS={'“', '”', '‘', '’'}):
            self.assertIsNone(disallowed_characters_validator(''))
            self.assertIsNone(disallowed_characters_validator('"\'string\''))

        with self.settings(DMOJ_PROBLEM_STATEMENT_DISALLOWED_CHARACTERS=set()):
            self.assertIsNone(disallowed_characters_validator(''))
            self.assertIsNone(disallowed_characters_validator('“”‘’'))

    def test_invalid(self):
        with self.settings(DMOJ_PROBLEM_STATEMENT_DISALLOWED_CHARACTERS={'“', '”', '‘', '’'}):
            with self.assertRaises(ValidationError, msg='Disallowed characters: “'):
                disallowed_characters_validator('“')
            with self.assertRaisesRegex(ValidationError, 'Disallowed characters: (?=.*‘)(?=.*’)'):
                disallowed_characters_validator('‘’')
