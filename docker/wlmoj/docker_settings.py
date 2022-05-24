BRIDGED_JUDGE_ADDRESS = (('0.0.0.0', 9999),)
BRIDGED_DJANGO_ADDRESS = (('0.0.0.0', 9998),)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'wlmoj_db',
        'USER': 'wlmoj_user',
        'PASSWORD': 'very_secure_password',
        'HOST': 'database',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'sql_mode': 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION',
        },
    },
}

# Redis for Celery
CELERY_BROKER_URL = 'redis://redis:6379'
CELERY_RESULT_BACKEND = 'redis://redis:6379'
