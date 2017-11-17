try:
    from snowpenguin.django.recaptcha2.fields import ReCaptchaField
    from snowpenguin.django.recaptcha2.widgets import ReCaptchaWidget
except ImportError:
    ReCaptchaField = None
    ReCaptchaWidget = None
else:
    from django.conf import settings
    if not hasattr(settings, 'RECAPTCHA_PRIVATE_KEY'):
        ReCaptchaField = None
        ReCaptchaWidget = None
