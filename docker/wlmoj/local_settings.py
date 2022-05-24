# This local_settings.py MUST only be used in Dockerfile setup, and **not** during production usage.

# ==================
# NOT FOR PRODUCTION
# ==================

import secrets

SECRET_KEY = secrets.token_hex(256)  # so it'll just be confusing
DEBUG = False

STATIC_ROOT = "/opt/wlmoj-static"

SITE_NAME = "WLMOJDT"
SITE_LONG_NAME = "WLMOJ Docker Test"
SITE_ADMIN_EMAIL = "test+wlmoj@nyiyui.ca"
TERMS_OF_SERVICE_URL = "/not-an-actual-page"

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "file": {
            "format": "%(levelname)s %(asctime)s %(module)s %(message)s",
        },
        "simple": {
            "format": "%(levelname)s %(message)s",
        },
    },
    "handlers": {
        # You may use this handler as example for logging to other files..
        "bridge": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "<desired bridge log path>",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "file",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "dmoj.throttle_mail.ThrottledEmailHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "file",
        },
    },
    "loggers": {
        # Site 500 error mails.
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        # Judging logs as received by bridged.
        "judge.bridge": {
            "handlers": ["bridge", "mail_admins"],
            "level": "INFO",
            "propagate": True,
        },
        # Catch all log to stderr.
        "": {
            "handlers": ["console"],
        },
        # Other loggers of interest. Configure at will.
        #  - judge.user: logs naughty user behaviours.
        #  - judge.problem.pdf: PDF generation log.
        #  - judge.html: HTML parsing errors when processing problem statements etc.
        #  - judge.mail.activate: logs for the reply to activate feature.
        #  - event_socket_server
    },
}
