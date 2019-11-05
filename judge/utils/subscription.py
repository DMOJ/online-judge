from django.conf import settings

if 'newsletter' in settings.INSTALLED_APPS:
    from newsletter.models import Subscription
else:
    Subscription = None

newsletter_id = None if Subscription is None else settings.DMOJ_NEWSLETTER_ID_ON_REGISTER
