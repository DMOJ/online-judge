from django.test import TestCase

from judge.models.tests.util import CommonDataMixin, create_blogpost, create_user


class BlogPostTestCase(CommonDataMixin, TestCase):
    @classmethod
    def setUpTestData(self):
        super().setUpTestData()
        self.users.update({
            'staff_blogpost_edit_own': create_user(
                username='staff_blogpost_edit_own',
                is_staff=True,
                user_permissions=('change_blogpost',),
            ),
            'staff_blogpost_edit_all': create_user(
                username='staff_blogpost_edit_all',
                is_staff=True,
                user_permissions=('change_blogpost', 'edit_all_post'),
            ),
        })

        self.basic_blogpost = create_blogpost(
            title='basic',
            authors=('staff_blogpost_edit_own',),
        )

        self.visible_blogpost = create_blogpost(
            title='visible',
            visible=True,
        )

    def test_basic_blogpost(self):
        self.assertEqual(str(self.basic_blogpost), self.basic_blogpost.title)

    def test_basic_blogpost_methods(self):
        data = {
            'superuser': {
                'can_see': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'staff_blogpost_edit_own': {
                'can_see': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'staff_blogpost_edit_all': {
                'can_see': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'normal': {
                'can_see': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
            'anonymous': {
                'can_see': self.assertFalse,
                'is_editable_by': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.basic_blogpost, data)

    def test_visible_blogpost_methods(self):
        data = {
            'superuser': {
                'can_see': self.assertTrue,
                'is_editable_by': self.assertTrue,
            },
            'staff_blogpost_edit_own': {
                'can_see': self.assertTrue,
                'is_editable_by': self.assertFalse,
            },
            'normal': {
                'can_see': self.assertTrue,
                'is_editable_by': self.assertFalse,
            },
            'anonymous': {
                'can_see': self.assertTrue,
                'is_editable_by': self.assertFalse,
            },
        }
        self._test_object_methods_with_users(self.visible_blogpost, data)
