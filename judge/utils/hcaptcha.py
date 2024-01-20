try:
    from hcaptcha_field import hCaptchaField, hCaptchaWidget
except ImportError:
    hCaptchaField = None
    hCaptchaWidget = None
else:
    from django.conf import settings
    if not hasattr(settings, 'HCAPTCHA_SECRET'):
        hCaptchaField = None
        hCaptchaWidget = None