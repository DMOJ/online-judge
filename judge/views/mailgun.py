import hashlib
import hmac
import logging
from email.utils import parseaddr

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from registration.models import RegistrationProfile

from judge.utils.unicode import utf8bytes

logger = logging.getLogger('judge.mail.activate')


class MailgunActivationView(View):
    if hasattr(settings, 'MAILGUN_ACCESS_KEY'):
        def post(self, request, *args, **kwargs):
            params = request.POST
            timestamp = params.get('timestamp', '')
            token = params.get('token', '')
            signature = params.get('signature', '')

            logger.debug('Received request: %s', params)

            if signature != hmac.new(key=utf8bytes(settings.MAILGUN_ACCESS_KEY),
                                     msg=utf8bytes('%s%s' % (timestamp, token)), digestmod=hashlib.sha256).hexdigest():
                logger.info('Rejected request: signature: %s, timestamp: %s, token: %s', signature, timestamp, token)
                raise PermissionDenied()
            _, sender = parseaddr(params.get('from'))
            if not sender:
                logger.info('Rejected invalid sender: %s', params.get('from'))
                return HttpResponse(status=406)
            try:
                user = User.objects.get(email__iexact=sender)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                logger.info('Rejected unknown sender: %s: %s', sender, params.get('from'))
                return HttpResponse(status=406)
            try:
                registration = RegistrationProfile.objects.get(user=user)
            except RegistrationProfile.DoesNotExist:
                logger.info('Rejected sender without RegistrationProfile: %s: %s', sender, params.get('from'))
                return HttpResponse(status=406)
            if registration.activated:
                logger.info('Rejected activated sender: %s: %s', sender, params.get('from'))
                return HttpResponse(status=406)

            key = registration.activation_key
            if key in params.get('body-plain', '') or key in params.get('body-html', ''):
                if RegistrationProfile.objects.activate_user(key, get_current_site(request)):
                    logger.info('Activated sender: %s: %s', sender, params.get('from'))
                    return HttpResponse('Activated', status=200)
                logger.info('Failed to activate sender: %s: %s', sender, params.get('from'))
            else:
                logger.info('Activation key not found: %s: %s', sender, params.get('from'))
            return HttpResponse(status=406)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(MailgunActivationView, self).dispatch(request, *args, **kwargs)
