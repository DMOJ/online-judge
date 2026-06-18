try:
    from snowpenguin.django.recaptcha2.fields import ReCaptchaField
    from snowpenguin.django.recaptcha2.widgets import ReCaptchaWidget
except ImportError:
    ReCaptchaField = None
    ReCaptchaWidget = None
try:
    from hcaptcha_field import hCaptchaField
except ImportError:
    hCaptchaField = None

from django.conf import settings

if not hasattr(settings, 'RECAPTCHA_PRIVATE_KEY') and ReCaptchaField is not None:
    ReCaptchaField = None
    ReCaptchaWidget = None
elif not hasattr(settings, 'HCAPTCHA_SECRET') and hCaptchaField is not None:
    hCaptchaField = None

CaptchaField = ReCaptchaField or hCaptchaField
