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
DEBUG = False
TEMPLATE_DEBUG = False

ALLOWED_HOSTS = []

SITE_ID = 1
SITE_NAME = 'DMOPC'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.flatpages',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'judge',
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
    'judge.timezone.TimezoneMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
)

ACCOUNT_ACTIVATION_DAYS = 7

ROOT_URLCONF = 'dmopc.urls'

WSGI_APPLICATION = 'dmopc.wsgi.application'

TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.request',
    'judge.template_context.user_profile',
    'judge.template_context.comet_location',
    'judge.template_context.general_info',
    'judge.template_context.site',
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

MARKDOWN_TROIS_STYLES = {
    'default': MARKDOWN_TROIS_DEFAULT_STYLE,
    'trusted': {
        'extras': {
            'code-friendly': None,
        },
        # Allow raw HTML (WARNING: don't use this for user-generated
        # Markdown for your site!).
        'safe_mode': False,
    },
    'comment': {
        'link_patterns': [
            (re.compile(r'\bproblem:(\w+)\b', re.I), r'/problem/\1'),
            # https://github.com/trentm/python-markdown2/wiki/link-patterns
            # I can not understand this regex. May be @tchrist can, but I certainly am not him.
            (re.compile(r'((([A-Za-z]{3,9}:(?:\/\/)?)(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:[0-9]+)?|(?:www\.|'
                        r'[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)((?:\/[\+~%\/\.\w\-_]*)?\??(?:[\-\+=&;%@\.\w_]*)#?'
                        r'(?:[\.\!\/\\\w]*))?)'), r'\1'),
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
    'problem': {
        'link_patterns': [
            (re.compile(r'((([A-Za-z]{3,9}:(?:\/\/)?)(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:[0-9]+)?|(?:www\.|'
                        r'[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)((?:\/[\+~%\/\.\w\-_]*)?\??(?:[\-\+=&;%@\.\w_]*)#?'
                        r'(?:[\.\!\/\\\w]*))?)'), r'\1'),
        ],
        'extras': {
            'code-friendly': None,
            'pyshell': None,
            'fenced-code-blocks': None,
            'demote-headers': 3,
            'link-patterns': None,
            'html-classes': {'pre': 'code'},
            'cuddled-lists': None,
            'footnotes': None,
            'header-ids': None,
        },
        'safe_mode': False,
    }
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

try:
    with open(os.path.join(os.path.dirname(__file__), 'local_settings.py')) as f:
        exec f in globals()
except IOError:
    pass
