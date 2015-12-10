"""
Django settings for dmoj project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '5*9f5q57mqmlz2#f$x1h76&jxy#yortjl1v+l*6hd18$d*yx#0'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

SITE_ID = 1
SITE_NAME = 'DMOJ'
SITE_LONG_NAME = 'Don Mills Online Judge'

PYGMENT_THEME = 'pygment-github.css'

# Application definition

INSTALLED_APPS = ()

try:
    import wpadmin
except ImportError:
    pass
else:
    del wpadmin
    INSTALLED_APPS += ('wpadmin',)

    WPADMIN = {
        'admin': {
            'title': 'Don Mills Online Judge Admin',
            'menu': {
                'top': 'wpadmin.menu.menus.BasicTopMenu',
                'left': 'wpadmin.menu.custom.CustomModelLeftMenuWithDashboard',
            },
            'custom_menu': [
                {
                    'model': 'auth.User',
                    'icon': 'fa-user',
                    'children': [
                        'auth.Group',
                        'registration.RegistrationProfile',
                    ],
                },
                {
                    'model': 'judge.Profile',
                    'icon': 'fa-user-plus',
                    'children': [
                        'judge.Organization',
                    ],
                },
                ('flatpages.FlatPage', 'fa-file-text-o'),
                {
                    'model': 'judge.Problem',
                    'icon': 'fa-question-circle',
                    'children': [
                        'judge.ProblemGroup',
                        'judge.ProblemType',
                    ],
                },
                ('judge.Solution', 'fa-pencil'),
                {
                    'model': 'judge.Contest',
                    'icon': 'fa-bar-chart',
                    'children': [
                        'judge.ContestParticipation',
                    ],
                },
                {
                    'model': 'judge.Submission',
                    'icon': 'fa-check-square-o',
                    'children': [
                        'judge.Language',
                        'judge.Judge',
                    ],
                },
            ],
            'dashboard': {
                'breadcrumbs': True,
            },
        }
    }

INSTALLED_APPS += (
    'django.contrib.admin',
    'judge',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.flatpages',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.redirects',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'registration',
    'markdown_trois',
    'mptt',
    'reversion',
    'reversion_compare',
    'django_social_share',
    'social.apps.django_app.default',
    'compressor',
    'django_ace',
    'pagedown',
    'sortedm2m',
)

MIDDLEWARE_CLASSES = (
    'judge.initialize.InitializationMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'judge.user_log.LogUserAccessMiddleware',
    'judge.timezone.TimezoneMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'judge.social_auth.SocialAuthExceptionMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
)

ACCOUNT_ACTIVATION_DAYS = 7

ROOT_URLCONF = 'dmoj.urls'
LOGIN_REDIRECT_URL = '/user'
WSGI_APPLICATION = 'dmoj.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            # This is to make django-suit use our own jQuery.
            # But we currently don't because we are still using select2 3.x.
            # os.path.join(BASE_DIR, 'dmoj', 'suit_template_patch'),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.media',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'judge.template_context.comet_location',
                'judge.template_context.get_resource',
                'judge.template_context.general_info',
                'judge.template_context.site',
                'judge.template_context.site_name',
                'judge.template_context.misc_config',
                'judge.template_context.contest',
                'social.apps.django_app.context_processors.backends',
                'social.apps.django_app.context_processors.login_redirect',
            ],
            'loaders': [
                ('pyjade.ext.django.Loader', (
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ))
            ]
        },
    },
]


# Markdown Trois
from markdown_trois.conf.settings import MARKDOWN_TROIS_DEFAULT_STYLE

markdown_admin_editable_style = {
    'extras': {
        'pyshell': None,
        'fenced-code-blocks': None,
        'html-classes': {'pre': 'code'},
        'cuddled-lists': None,
        'footnotes': None,
        'header-ids': None,
        'demote-headers': 2,
        'tables': None,
    },
    'safe_mode': False,
}

MARKDOWN_TROIS_STYLES = {
    'default': MARKDOWN_TROIS_DEFAULT_STYLE,
    'trusted': {
        'extras': {
            'code-friendly': None,
            'pyshell': None,
            'fenced-code-blocks': None,
            'html-classes': {'pre': 'code'},
            'cuddled-lists': None,
            'footnotes': None,
            'header-ids': None,
        },
        # Allow raw HTML (WARNING: don't use this for user-generated
        # Markdown for your site!).
        'safe_mode': False,
    },
    'comment': {
        'link_patterns': [
            (re.compile(r'\bproblem:(\w+)\b', re.I), r'/problem/\1'),
            (re.compile(r'\bsubmission:(\w+)\b', re.I), r'/submission/\1'),
            (re.compile(r'@(\w+)\b', re.I), r'/user/\1'),
        ],
        'extras': {
            'code-friendly': None,
            'pyshell': None,
            'fenced-code-blocks': None,
            'demote-headers': 3,
            'link-patterns': None,
            'nofollow': None,
            'html-classes': {'pre': 'code'},
            'cuddled-lists': None,
            'footnotes': None,
            'header-ids': None,
        },
        'safe_mode': 'escape',
    },
    'self-description': {
        'extras': {
            'code-friendly': None,
            'pyshell': None,
            'fenced-code-blocks': None,
            'demote-headers': 3,
            'nofollow': None,
            'html-classes': {'pre': 'code'},
            'cuddled-lists': None,
            'header-ids': None,
        },
        'safe_mode': 'escape',
    },
    'problem': markdown_admin_editable_style,
    'contest': markdown_admin_editable_style,
    'language': markdown_admin_editable_style,
    'license': markdown_admin_editable_style,
    'judge': markdown_admin_editable_style,
    'blog': markdown_admin_editable_style,
    'organization-about': {
        'extras': {
            'code-friendly': None,
            'pyshell': None,
            'fenced-code-blocks': None,
            'demote-headers': 3,
            'nofollow': None,
            'html-classes': {'pre': 'code'},
            'cuddled-lists': None,
            'header-ids': None,
        },
        'safe_mode': 'escape',
    },
}

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

ENABLE_FTS = False

# Bridged configuration
BRIDGED_JUDGE_HOST = 'localhost'
BRIDGED_JUDGE_PORT = 9999
BRIDGED_DJANGO_HOST = 'localhost'
BRIDGED_DJANGO_PORT = 9998

# Event Server configuration
EVENT_DAEMON_USE = True
EVENT_DAEMON_POST = 'ws://localhost:9997/'
EVENT_DAEMON_GET = 'ws://localhost:9996/'
EVENT_DAEMON_POLL = '/channels/'
EVENT_DAEMON_KEY = None

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
DEFAULT_USER_TIME_ZONE = 'America/Toronto'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

DMOJ_RESOURCES = os.path.join(BASE_DIR, 'resources')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'resources'),
]
STATIC_URL = '/static/'

# Define a cache
CACHES = {}

# Authentication
AUTHENTICATION_BACKENDS = (
    'social.backends.google.GoogleOAuth2',
    'social.backends.dropbox.DropboxOAuth2',
    'social.backends.facebook.FacebookOAuth2',
    'judge.social_auth.GitHubSecureEmailOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'judge.social_auth.verify_email',
    'social.pipeline.social_auth.social_user',
    'social.pipeline.user.get_username',
    'social.pipeline.social_auth.associate_by_email',
    'judge.social_auth.choose_username',
    'social.pipeline.user.create_user',
    'judge.social_auth.make_profile',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details'
)

SOCIAL_AUTH_GITHUB_SECURE_SCOPE = ['user:email']
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']
SOCIAL_AUTH_SLUGIFY_USERNAMES = True
SOCIAL_AUTH_SLUGIFY_FUNCTION = 'judge.social_auth.slugify_username'

JUDGE_AMQP_PATH = None


try:
    with open(os.path.join(os.path.dirname(__file__), 'local_settings.py')) as f:
        exec f in globals()
except IOError:
    pass
