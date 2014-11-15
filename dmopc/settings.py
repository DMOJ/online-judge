"""
Django settings for dmopc project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '5*9f5q57mqmlz2#f$x1h76&jxy#yortjl1v+l*6hd18$d*yx#0'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

SITE_ID = 1
SITE_NAME = 'DMOPC'

# Application definition

INSTALLED_APPS = ()

try:
    import suit
except ImportError:
    pass
else:
    del suit
    INSTALLED_APPS += ('suit',)
    SUIT_CONFIG = {
        'ADMIN_NAME': 'DMOJ Admin',
        'LIST_PER_PAGE': 100,
        'MENU': (
            {
                'label': 'Site',
                'icon': 'icon-leaf',
                'models': (
                    'sites.site',
                    'flatpages.flatpage',
                    'judge.miscconfig',
                    'judge.navigationbar'
                ),
            },
            {
                'label': 'Users',
                'icon': 'icon-user',
                'models': (
                    'auth.user',
                    'auth.group',
                    'judge.profile',
                    'judge.organization',
                    'registration.registrationprofile',
                ),
            },
            {
                'label': 'Problems',
                'icon': 'icon-question-sign',
                'models': (
                    'judge.problem',
                    'judge.problemgroup',
                    'judge.problemtype',
                    'judge.contest',
                ),
            },
            {
                'label': 'Judging',
                'icon': 'icon-ok',
                'models': (
                    'judge.submission',
                    'judge.language',
                    'judge.judge',
                ),
            }
        )
    }

INSTALLED_APPS += (
    'django.contrib.admin',
    'judge',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.flatpages',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'registration',
    'markdown_trois',
)

MIDDLEWARE_CLASSES = (
    'judge.initialize.InitializationMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'judge.user_log.LogUserAccessMiddleware',
    'judge.timezone.TimezoneMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
)

ACCOUNT_ACTIVATION_DAYS = 7

ROOT_URLCONF = 'dmopc.urls'

WSGI_APPLICATION = 'dmopc.wsgi.application'

TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.request',
    'judge.template_context.comet_location',
    'judge.template_context.general_info',
    'judge.template_context.site',
    'judge.template_context.misc_config',
    'judge.template_context.contest',
)

TEMPLATE_LOADERS = (
    ('pyjade.ext.django.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

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
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'resources'),
]
STATIC_URL = '/static/'

# Define a cache
CACHES = {
    'fast': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'dmoj-fast-memory'
    }
}

try:
    with open(os.path.join(os.path.dirname(__file__), 'local_settings.py')) as f:
        exec f in globals()
except IOError:
    pass
