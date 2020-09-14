from django.contrib.auth.models import AnonymousUser, Permission, User
from django.utils import timezone

from judge.models import BlogPost, Contest, ContestParticipation, ContestProblem, ContestTag, Language, Organization, \
    Problem, ProblemGroup, ProblemType, Profile, Solution


class CreateModel:
    model = None
    m2m_fields = {}
    required_fields = ()

    def get_defaults(self, required_kwargs, kwargs):
        return {}

    def get_m2m_data(self, required_kwargs, defaults):
        return {key: defaults.pop(key, ()) for key in self.m2m_fields}

    def process_related_objects(self, required_kwargs, defaults):
        pass

    def on_created_object(self, obj):
        pass

    def __call__(self, *args, **kwargs):
        # in case the required fields are passed as arguments instead of keyword arguments
        if len(args) == len(self.required_fields):
            for field, arg in zip(self.required_fields, args):
                kwargs[field] = arg

        for field in self.required_fields:
            if field not in kwargs:
                raise ValueError('%s field is required.' % field)

        required_kwargs = {key: kwargs.pop(key) for key in self.required_fields}

        defaults = self.get_defaults(required_kwargs, kwargs)
        defaults.update(kwargs)

        m2m_data = self.get_m2m_data(required_kwargs, defaults)
        self.process_related_objects(required_kwargs, defaults)

        obj, created = self.model.objects.get_or_create(
            **required_kwargs,
            defaults=defaults,
        )

        if created:
            for field, relationship in self.m2m_fields.items():
                related_model, query_field = relationship
                getattr(obj, field).set(related_model.objects.filter(**{query_field + '__in': m2m_data[field]}))

            self.on_created_object(obj)

        return obj


class CreateBlogPost(CreateModel):
    model = BlogPost
    m2m_fields = {
        'authors': (Profile, 'user__username'),
    }
    required_fields = ('title',)

    def get_defaults(self, required_kwargs, kwargs):
        _now = timezone.now()
        return {
            'slug': required_kwargs['title'],
            'publish_on': _now - timezone.timedelta(days=100),
        }


create_blogpost = CreateBlogPost()


class CreateUser(CreateModel):
    model = User
    m2m_fields = {
        'user_permissions': (Permission, 'codename'),
    }
    required_fields = ('username',)

    def on_created_object(self, obj):
        Profile.objects.get_or_create(user=obj)


create_user = CreateUser()


class CreateOrganization(CreateModel):
    model = Organization
    m2m_fields = {
        'admins': (Profile, 'user__username'),
    }
    required_fields = ('name',)

    def get_defaults(self, required_kwargs, kwargs):
        return {
            'slug': required_kwargs['name'],
            'short_name': required_kwargs['name'],
        }

    def process_related_objects(self, required_kwargs, defaults):
        if not isinstance(defaults['registrant'], Profile):
            defaults['registrant'] = create_user(defaults['registrant']).profile


create_organization = CreateOrganization()


class CreateProblemGroup(CreateModel):
    model = ProblemGroup
    required_fields = ('name',)

    def get_defaults(self, required_kwargs, kwargs):
        return {
            'full_name': required_kwargs['name'],
        }


create_problem_group = CreateProblemGroup()


class CreateProblemType(CreateModel):
    model = ProblemType
    required_fields = ('name',)

    def get_defaults(self, required_kwargs, kwargs):
        return {
            'full_name': required_kwargs['name'],
        }


create_problem_type = CreateProblemType()


class CreateProblem(CreateModel):
    model = Problem
    m2m_fields = {
        'authors': (Profile, 'user__username'),
        'curators': (Profile, 'user__username'),
        'testers': (Profile, 'user__username'),
        'types': (ProblemType, 'name'),
        'allowed_languages': (Language, 'key'),
        'banned_users': (Profile, 'user__username'),
        'organizations': (Organization, 'name'),
    }
    required_fields = ('code',)

    def get_defaults(self, required_kwargs, kwargs):
        return {
            'name': required_kwargs['code'],
            'description': '',
            'time_limit': 1,
            'memory_limit': 65536,
            'points': 1,
            'group': 'group',
        }

    def process_related_objects(self, required_kwargs, defaults):
        if not isinstance(defaults['group'], ProblemGroup):
            defaults['group'] = create_problem_group(defaults['group'])


create_problem = CreateProblem()


class CreateSolution(CreateModel):
    model = Solution
    m2m_fields = {
        'authors': (Profile, 'user__username'),
    }
    required_fields = ('problem',)

    def get_defaults(self, required_kwargs, kwargs):
        _now = timezone.now()
        return {
            'is_public': True,
            'publish_on': _now - timezone.timedelta(days=4),
            'content': '',
        }

    def process_related_objects(self, required_kwargs, defaults):
        if not isinstance(required_kwargs['problem'], Problem):
            required_kwargs['problem'] = create_problem(required_kwargs['problem'])


create_solution = CreateSolution()


class CreateContest(CreateModel):
    model = Contest
    m2m_fields = {
        'organizers': (Profile, 'user__username'),
        'problems': (Problem, 'code'),
        'view_contest_scoreboard': (Profile, 'user__username'),
        'rate_exclude': (Profile, 'user__username'),
        'private_contestants': (Profile, 'user__username'),
        'organizations': (Organization, 'name'),
        'tags': (ContestTag, 'name'),
        'banned_users': (Profile, 'user__username'),
    }
    required_fields = ('key',)

    def get_defaults(self, required_kwargs, kwargs):
        _now = timezone.now()
        return {
            'name': required_kwargs['key'],
            'description': '',
            'start_time': _now - timezone.timedelta(days=100),
            'end_time': _now + timezone.timedelta(days=100),
        }


create_contest = CreateContest()


class CreateContestParticipation(CreateModel):
    model = ContestParticipation
    required_fields = ('contest', 'user')

    def process_related_objects(self, required_kwargs, defaults):
        if not isinstance(required_kwargs['contest'], Contest):
            required_kwargs['contest'] = create_contest(required_kwargs['contest'])
        if not isinstance(required_kwargs['user'], Profile):
            required_kwargs['user'] = create_user(required_kwargs['user']).profile


create_contest_participation = CreateContestParticipation()


class CreateContestProblem(CreateModel):
    model = ContestProblem
    required_fields = ('contest', 'problem')

    def get_defaults(self, required_kwargs, kwargs):
        return {
            'points': 100,
            'order': 1,
        }

    def process_related_objects(self, required_kwargs, defaults):
        if not isinstance(required_kwargs['contest'], Contest):
            required_kwargs['contest'] = create_contest(required_kwargs['contest'])
        if not isinstance(required_kwargs['problem'], Problem):
            required_kwargs['problem'] = create_problem(required_kwargs['problem'])


create_contest_problem = CreateContestProblem()


class CommonDataMixin:
    fixtures = ['language_all.json']

    @classmethod
    def setUpTestData(self):
        self.users = {
            'superuser': create_user(
                username='superuser',
                is_superuser=True,
                is_staff=True,
            ),
            'staff_problem_edit_own': create_user(
                username='staff_problem_edit_own',
                is_staff=True,
                user_permissions=('edit_own_problem', 'rejudge_submission'),
            ),
            'staff_problem_see_all': create_user(
                username='staff_problem_see_all',
                user_permissions=('see_private_problem',),
            ),
            'staff_problem_edit_all': create_user(
                username='staff_problem_edit_all',
                is_staff=True,
                user_permissions=('edit_own_problem', 'edit_all_problem'),
            ),
            'staff_problem_edit_public': create_user(
                username='staff_problem_edit_public',
                is_staff=True,
                user_permissions=('edit_own_problem', 'edit_public_problem'),
            ),
            'staff_problem_see_organization': create_user(
                username='staff_problem_see_organization',
                user_permissions=('see_organization_problem',),
            ),
            'staff_problem_edit_all_with_rejudge': create_user(
                username='staff_problem_edit_all_with_rejudge',
                is_staff=True,
                user_permissions=('edit_own_problem', 'edit_all_problem', 'rejudge_submission'),
            ),
            'staff_problem_edit_own_no_staff': create_user(
                username='staff_problem_edit_own_no_staff',
                user_permissions=('edit_own_problem', 'rejudge_submission'),
            ),
            'normal': create_user(
                username='normal',
            ),
            'anonymous': AnonymousUser(),
        }

        self.organizations = {
            'open': create_organization(
                name='open',
                registrant='superuser',
            ),
        }

    def _test_object_methods_with_users(self, obj, data):
        for username, methods in data.items():
            with self.subTest(username=username, object=str(obj)):
                for method, func in methods.items():
                    with self.subTest(method=method):
                        func(
                            getattr(obj, method)(self.users[username]),
                            msg='Method "%s" failed for user "%s", object "%s".' % (method, username, obj),
                        )
