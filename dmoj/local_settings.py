import ldap
from django_auth_ldap.config import LDAPSearch

STATIC_ROOT = "/dmoj/site/static/"
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/dmoj/site/cache/',
    }
}
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'dmoj',
        'USER': 'dmoj',
        'PASSWORD': 'dmoj',
        'HOST': '172.25.3.3',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'sql_mode': 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION',
	},
    }
}
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', u'*']
AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AUTH_LDAP_SERVER_URI = 'ldaps://XXX'

AUTH_LDAP_BIND_DN = 'uid=XXX,ou=XXX,dc=XXX'
AUTH_LDAP_BIND_PASSWORD = 'XXX'
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    'ou=XXX,dc=XXX',
    ldap.SCOPE_SUBTREE,
    '(uid=%(user)s)',
)
AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': 'givenName',
    'last_name': 'sn',
    'email': 'mail',
}

AUTH_LDAP_ALWAYS_UPDATE_USER = True
AUTH_LDAP_FIND_GROUP_PERMS = False
ldap.set_option( ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER ) 
AUTH_LDAP_AUTHORIZE_ALL_USERS = True

ACE_URL = '/dmoj/static/libs/ace/'

USE_I18N = True
USE_L10N = True
USE_TZ = True

## Bridge controls.
# The judge connection address and port; where the judges will connect to the site.
# You should change this to something your judges can actually connect to 
# (e.g., a port that is unused and unblocked by a firewall).
BRIDGED_JUDGE_ADDRESS = [('0.0.0.0', 9999)]
#BRIDGED_JUDGE_HOST = 'host'
#BRIDGED_JUDGE_PORT = 9999

# The bridged daemon bind address and port to communicate with the site.
BRIDGED_DJANGO_ADDRESS = [('0.0.0.0', 9998)]
#BRIDGED_DJANGO_HOST = 'host'
#BRIDGED_DJANGO_PORT = 9998

## DMOJ features.
# Set to True to enable full-text searching for problems.
ENABLE_FTS = True

EVENT_DAEMON_USE = True
EVENT_DAEMON_GET = 'ws://127.0.0.1/event/'
EVENT_DAEMON_POST = 'ws://127.0.0.1:15101/'
EVENT_DAEMON_POLL = '/channels/'
EVENT_DAEMON_KEY = None

