"""
Django settings for dmoj project.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import tempfile

from django.utils.translation import ugettext_lazy as _
from django_jinja.builtins import DEFAULT_EXTENSIONS
from jinja2 import select_autoescape

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '5*9f5q57mqmlz2#f$x1h76&jxy#yortjl1v+l*6hd18$d*yx#0'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

SITE_ID = 1
SITE_NAME = 'DMOJ'
SITE_LONG_NAME = 'DMOJ: Modern Online Judge'
SITE_ADMIN_EMAIL = False

DMOJ_REQUIRE_STAFF_2FA = True

# Set to 1 to use HTTPS if request was made to https://
# Set to 2 to always use HTTPS for links
# Set to 0 to always use HTTP for links
DMOJ_SSL = 0

# Refer to dmoj.ca/post/103-point-system-rework
DMOJ_PP_STEP = 0.95
DMOJ_PP_ENTRIES = 100
DMOJ_PP_BONUS_FUNCTION = lambda n: 300 * (1 - 0.997 ** n)  # noqa: E731

NODEJS = '/usr/bin/node'
EXIFTOOL = '/usr/bin/exiftool'
ACE_URL = '//cdnjs.cloudflare.com/ajax/libs/ace/1.1.3'
SELECT2_JS_URL = '//cdnjs.cloudflare.com/ajax/libs/select2/4.0.3/js/select2.min.js'
DEFAULT_SELECT2_CSS = '//cdnjs.cloudflare.com/ajax/libs/select2/4.0.3/css/select2.min.css'

DMOJ_CAMO_URL = None
DMOJ_CAMO_KEY = None
DMOJ_CAMO_HTTPS = False
DMOJ_CAMO_EXCLUDE = ()
DMOJ_PROBLEM_DATA_ROOT = None
DMOJ_PROBLEM_MIN_TIME_LIMIT = 0  # seconds
DMOJ_PROBLEM_MAX_TIME_LIMIT = 60  # seconds
DMOJ_PROBLEM_MIN_MEMORY_LIMIT = 0  # kilobytes
DMOJ_PROBLEM_MAX_MEMORY_LIMIT = 1048576  # kilobytes
DMOJ_PROBLEM_MIN_PROBLEM_POINTS = 0
DMOJ_RATING_COLORS = True
DMOJ_EMAIL_THROTTLING = (10, 60)
DMOJ_STATS_LANGUAGE_THRESHOLD = 10
DMOJ_SUBMISSIONS_REJUDGE_LIMIT = 10
# Maximum number of submissions a single user can queue without the `spam_submission` permission
DMOJ_SUBMISSION_LIMIT = 2
DMOJ_BLOG_NEW_PROBLEM_COUNT = 7
DMOJ_BLOG_RECENTLY_ATTEMPTED_PROBLEMS_COUNT = 7
DMOJ_TOTP_TOLERANCE_HALF_MINUTES = 1
DMOJ_USER_MAX_ORGANIZATION_COUNT = 3
DMOJ_COMMENT_VOTE_HIDE_THRESHOLD = -5
DMOJ_PDF_PROBLEM_CACHE = ''
DMOJ_PDF_PROBLEM_TEMP_DIR = tempfile.gettempdir()
DMOJ_STATS_SUBMISSION_RESULT_COLORS = {
    'TLE': '#a3bcbd',
    'AC': '#00a92a',
    'WA': '#ed4420',
    'CE': '#42586d',
    'ERR': '#ffa71c',
}
DMOJ_API_PAGE_SIZE = 1000

MARKDOWN_STYLES = {}
MARKDOWN_DEFAULT_STYLE = {}

MATHOID_URL = False
MATHOID_GZIP = False
MATHOID_MML_CACHE = None
MATHOID_CSS_CACHE = 'default'
MATHOID_DEFAULT_TYPE = 'auto'
MATHOID_MML_CACHE_TTL = 86400
MATHOID_CACHE_ROOT = ''
MATHOID_CACHE_URL = False

TEXOID_GZIP = False
TEXOID_META_CACHE = 'default'
TEXOID_META_CACHE_TTL = 86400
DMOJ_NEWSLETTER_ID_ON_REGISTER = None

BAD_MAIL_PROVIDERS = ()
BAD_MAIL_PROVIDER_REGEX = ()
NOFOLLOW_EXCLUDED = set()

TIMEZONE_BG = None
TIMEZONE_MAP = None
TIMEZONE_DETECT_BACKEND = None

TERMS_OF_SERVICE_URL = None
DEFAULT_USER_LANGUAGE = 'PY3'

PHANTOMJS = ''
PHANTOMJS_PDF_ZOOM = 0.75
PHANTOMJS_PDF_TIMEOUT = 5.0
PHANTOMJS_PAPER_SIZE = 'Letter'

SLIMERJS = ''
SLIMERJS_PDF_ZOOM = 0.75
SLIMERJS_FIREFOX_PATH = ''
SLIMERJS_PAPER_SIZE = 'Letter'

PUPPETEER_MODULE = '/usr/lib/node_modules/puppeteer'
PUPPETEER_PAPER_SIZE = 'Letter'

USE_SELENIUM = False
SELENIUM_CUSTOM_CHROME_PATH = None
SELENIUM_CHROMEDRIVER_PATH = 'chromedriver'

PYGMENT_THEME = 'pygment-github.css'
INLINE_JQUERY = True
INLINE_FONTAWESOME = True
JQUERY_JS = '//ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js'
FONTAWESOME_CSS = '//maxcdn.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.min.css'
DMOJ_CANONICAL = ''

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
            'title': 'DMOJ Admin',
            'menu': {
                'top': 'wpadmin.menu.menus.BasicTopMenu',
                'left': 'wpadmin.menu.custom.CustomModelLeftMenuWithDashboard',
            },
            'custom_menu': [
                {
                    'model': 'judge.Problem',
                    'icon': 'fa-question-circle',
                    'children': [
                        'judge.ProblemGroup',
                        'judge.ProblemType',
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
                {
                    'model': 'judge.Contest',
                    'icon': 'fa-bar-chart',
                    'children': [
                        'judge.ContestParticipation',
                        'judge.ContestTag',
                    ],
                },
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
                        'judge.OrganizationRequest',
                    ],
                },
                {
                    'model': 'judge.NavigationBar',
                    'icon': 'fa-bars',
                    'children': [
                        'judge.MiscConfig',
                        'judge.License',
                        'sites.Site',
                        'redirects.Redirect',
                    ],
                },
                ('judge.BlogPost', 'fa-rss-square'),
                ('judge.Comment', 'fa-comment-o'),
                ('flatpages.FlatPage', 'fa-file-text-o'),
                ('judge.Solution', 'fa-pencil'),
            ],
            'dashboard': {
                'breadcrumbs': True,
            },
        },
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
    'mptt',
    'reversion',
    'django_social_share',
    'social_django',
    'compressor',
    'django_ace',
    'pagedown',
    'sortedm2m',
    'statici18n',
    'impersonate',
    'django_jinja',
    'martor',
)

MIDDLEWARE = (
    'judge.middleware.ShortCircuitMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'judge.middleware.APIMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'judge.middleware.DMOJLoginMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'judge.user_log.LogUserAccessMiddleware',
    'judge.timezone.TimezoneMiddleware',
    'impersonate.middleware.ImpersonateMiddleware',
    'judge.middleware.DMOJImpersonationMiddleware',
    'judge.middleware.ContestMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'judge.social_auth.SocialAuthExceptionMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
)

IMPERSONATE_REQUIRE_SUPERUSER = True
IMPERSONATE_DISABLE_LOGGING = True

ACCOUNT_ACTIVATION_DAYS = 7

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'judge.utils.pwned.PwnedPasswordsValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

SILENCED_SYSTEM_CHECKS = ['urls.W002', 'fields.W342']

ROOT_URLCONF = 'dmoj.urls'
LOGIN_REDIRECT_URL = '/user'
WSGI_APPLICATION = 'dmoj.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django_jinja.backend.Jinja2',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': False,
        'OPTIONS': {
            'match_extension': ('.html', '.txt'),
            'match_regex': '^(?!admin/)',
            'context_processors': [
                'django.template.context_processors.media',
                'django.template.context_processors.tz',
                'django.template.context_processors.i18n',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'judge.template_context.comet_location',
                'judge.template_context.get_resource',
                'judge.template_context.general_info',
                'judge.template_context.site',
                'judge.template_context.site_name',
                'judge.template_context.misc_config',
                'judge.template_context.math_setting',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
            'autoescape': select_autoescape(['html', 'xml']),
            'trim_blocks': True,
            'lstrip_blocks': True,
            'extensions': DEFAULT_EXTENSIONS + [
                'compressor.contrib.jinja2ext.CompressorExtension',
                'judge.jinja2.DMOJExtension',
                'judge.jinja2.spaceless.SpacelessExtension',
            ],
        },
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.media',
                'django.template.context_processors.tz',
                'django.template.context_processors.i18n',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

LANGUAGES = [
    ('de', _('German')),
    ('en', _('English')),
    ('es', _('Spanish')),
    ('fr', _('French')),
    ('hr', _('Croatian')),
    ('hu', _('Hungarian')),
    ('ja', _('Japanese')),
    ('ko', _('Korean')),
    ('pt', _('Brazilian Portuguese')),
    ('ro', _('Romanian')),
    ('ru', _('Russian')),
    ('sr-latn', _('Serbian (Latin)')),
    ('tr', _('Turkish')),
    ('vi', _('Vietnamese')),
    ('zh-hans', _('Simplified Chinese')),
    ('zh-hant', _('Traditional Chinese')),
]

MARKDOWN_ADMIN_EDITABLE_STYLE = {
    'safe_mode': False,
    'use_camo': True,
    'texoid': True,
    'math': True,
}

MARKDOWN_DEFAULT_STYLE = {
    'safe_mode': True,
    'nofollow': True,
    'use_camo': True,
    'math': True,
}

MARKDOWN_USER_LARGE_STYLE = {
    'safe_mode': True,
    'nofollow': True,
    'use_camo': True,
    'math': True,
}

MARKDOWN_STYLES = {
    'default': MARKDOWN_DEFAULT_STYLE,
    'comment': MARKDOWN_DEFAULT_STYLE,
    'self-description': MARKDOWN_USER_LARGE_STYLE,
    'problem': MARKDOWN_ADMIN_EDITABLE_STYLE,
    'contest': MARKDOWN_ADMIN_EDITABLE_STYLE,
    'flatpage': MARKDOWN_ADMIN_EDITABLE_STYLE,
    'language': MARKDOWN_ADMIN_EDITABLE_STYLE,
    'license': MARKDOWN_ADMIN_EDITABLE_STYLE,
    'judge': MARKDOWN_ADMIN_EDITABLE_STYLE,
    'blog': MARKDOWN_ADMIN_EDITABLE_STYLE,
    'solution': MARKDOWN_ADMIN_EDITABLE_STYLE,
    'contest_tag': MARKDOWN_ADMIN_EDITABLE_STYLE,
    'organization-about': MARKDOWN_USER_LARGE_STYLE,
    'ticket': MARKDOWN_USER_LARGE_STYLE,
}

MARTOR_ENABLE_CONFIGS = {
    'imgur': 'true',
    'mention': 'true',
    'jquery': 'true',
    'living': 'false',
    'spellcheck': 'false',
    'hljs': 'false',
}
MARTOR_MARKDOWNIFY_URL = '/widgets/preview/default'
MARTOR_SEARCH_USERS_URL = '/widgets/martor/search-user'
MARTOR_UPLOAD_URL = '/widgets/martor/upload-image'
MARTOR_MARKDOWN_BASE_MENTION_URL = '/user/'

# Directory under MEDIA_ROOT to use to store image uploaded through martor.
MARTOR_UPLOAD_MEDIA_DIR = 'martor'
MARTOR_UPLOAD_SAFE_EXTS = {'.jpg', '.png', '.gif'}

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    },
}

ENABLE_FTS = False

# Bridged configuration
BRIDGED_JUDGE_ADDRESS = [('localhost', 9999)]
BRIDGED_JUDGE_PROXIES = None
BRIDGED_DJANGO_ADDRESS = [('localhost', 9998)]
BRIDGED_DJANGO_CONNECT = None

# Event Server configuration
EVENT_DAEMON_USE = False
EVENT_DAEMON_POST = 'ws://localhost:9997/'
EVENT_DAEMON_GET = 'ws://localhost:9996/'
EVENT_DAEMON_POLL = '/channels/'
EVENT_DAEMON_KEY = None
EVENT_DAEMON_AMQP_EXCHANGE = 'dmoj-events'
EVENT_DAEMON_SUBMISSION_KEY = '6Sdmkx^%pk@GsifDfXcwX*Y7LRF%RGT8vmFpSxFBT$fwS7trc8raWfN#CSfQuKApx&$B#Gh2L7p%W!Ww'

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

# Whatever you do, this better be one of the entries in `LANGUAGES`.
LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
DEFAULT_USER_TIME_ZONE = 'America/Toronto'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Cookies
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

DMOJ_RESOURCES = os.path.join(BASE_DIR, 'resources')
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'resources'),
]
STATIC_URL = '/static/'

# Define a cache
CACHES = {}

# Authentication
AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.facebook.FacebookOAuth2',
    'judge.social_auth.GitHubSecureEmailOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'judge.social_auth.verify_email',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.social_auth.associate_by_email',
    'judge.social_auth.choose_username',
    'social_core.pipeline.user.create_user',
    'judge.social_auth.make_profile',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

SOCIAL_AUTH_GITHUB_SECURE_SCOPE = ['user:email']
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']
SOCIAL_AUTH_SLUGIFY_USERNAMES = True
SOCIAL_AUTH_SLUGIFY_FUNCTION = 'judge.social_auth.slugify_username'

JUDGE_AMQP_PATH = None

MOSS_API_KEY = None

CELERY_WORKER_HIJACK_ROOT_LOGGER = False

WEBAUTHN_RP_ID = None

try:
    with open(os.path.join(os.path.dirname(__file__), 'local_settings.py')) as f:
        exec(f.read(), globals())
except IOError:
    pass
