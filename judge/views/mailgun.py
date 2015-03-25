import hashlib
import hmac
from email.utils import parseaddr

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views.generic import View
from registration.models import RegistrationProfile


if hasattr(settings, 'MAILGUN_ACCESS_KEY'):
    class MailgunActivationView(View):
        def post(self, request, *args, **kwargs):
            params = request.POST
            timestamp = params.get('timestamp', '')
            token = params.get('token', '')
            signature = params.get('signature', '')

            print request.POST

            if signature != hmac.new(key=settings.MAILGUN_ACCESS_KEY, msg='%s%s' % (timestamp, token),
                                     digestmod=hashlib.sha256).hexdigest():
                raise PermissionDenied()
            _, sender = parseaddr(params.get('from'))
            if not sender:
                return HttpResponse(status=406)
            try:
                user = User.objects.get(email__iexact=sender)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                return HttpResponse(status=406)
            try:
                registration = RegistrationProfile.objects.get(user=user)
            except RegistrationProfile.DoesNotExist:
                return HttpResponse(status=406)
            key = registration.activation_key
            if key == RegistrationProfile.ACTIVATED:
                return HttpResponse(status=406)

            if key in params.get('body-plain', '') or key in params.get('body-html', ''):
                if RegistrationProfile.objects.activate_user(key):
                    return HttpResponse('Activated', status=200)
            return HttpResponse(status=406)
else:
    class MailgunActivationView(View):
        pass