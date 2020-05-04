import base64
import json
import os
from io import BytesIO

import pyotp
import qrcode
import webauthn
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import SuccessURLAllowedHostsMixin
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse, Http404, HttpResponse
from django.urls import reverse
from django.utils.http import is_safe_url
from django.utils.translation import gettext as _
from django.views.generic import FormView, View

from judge.forms import TOTPForm
from judge.jinja2.gravatar import gravatar
from judge.models import WebAuthnCredential
from judge.utils.views import TitleMixin


class TOTPView(TitleMixin, LoginRequiredMixin, FormView):
    form_class = TOTPForm

    def get_form_kwargs(self):
        result = super(TOTPView, self).get_form_kwargs()
        result['profile'] = self.profile
        return result

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.profile = self.request.profile
            if self.check_skip():
                return self.next_page()
        return super(TOTPView, self).dispatch(request, *args, **kwargs)

    def check_skip(self):
        raise NotImplementedError()

    def next_page(self):
        return HttpResponseRedirect(reverse('user_edit_profile'))


class TOTPEnableView(TOTPView):
    title = _('Enable Two Factor Authentication')
    template_name = 'registration/totp_enable.html'

    def get(self, request, *args, **kwargs):
        profile = self.profile
        if not profile.totp_key:
            profile.totp_key = pyotp.random_base32(length=32)
            profile.save()
        return self.render_to_response(self.get_context_data())

    def check_skip(self):
        return self.profile.is_totp_enabled

    def post(self, request, *args, **kwargs):
        if not self.profile.totp_key:
            return HttpResponseBadRequest('No TOTP key generated on server side?')
        return super(TOTPEnableView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TOTPEnableView, self).get_context_data(**kwargs)
        context['totp_key'] = self.profile.totp_key
        context['qr_code'] = self.render_qr_code(self.request.user.username, self.profile.totp_key)
        return context

    def form_valid(self, form):
        self.profile.is_totp_enabled = True
        self.profile.save()
        # Make sure users don't get prompted to enter code right after enabling:
        self.request.session['2fa_passed'] = True
        return self.next_page()

    @classmethod
    def render_qr_code(cls, username, key):
        totp = pyotp.TOTP(key)
        uri = totp.provisioning_uri(username, settings.SITE_NAME)

        qr = qrcode.QRCode(box_size=1)
        qr.add_data(uri)
        qr.make(fit=True)

        image = qr.make_image(fill_color='black', back_color='white')
        buf = BytesIO()
        image.save(buf, format='PNG')
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


class TOTPDisableView(TOTPView):
    title = _('Disable Two Factor Authentication')
    template_name = 'registration/totp_disable.html'

    def check_skip(self):
        if not self.profile.is_totp_enabled:
            return True
        return settings.DMOJ_REQUIRE_STAFF_2FA and self.request.user.is_staff

    def form_valid(self, form):
        self.profile.is_totp_enabled = False
        self.profile.totp_key = None
        self.profile.save()
        return self.next_page()


class WebAuthnView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not settings.WEBAUTHN_RP_ID:
            raise Http404()
        return super(WebAuthnView, self).dispatch(request, *args, **kwargs)


def webauthn_encode(binary):
    return base64.urlsafe_b64encode(binary).decode('ascii').rstrip('=')


def webauthn_decode(text):
    text += '=' * (-len(text) % 4)
    return base64.urlsafe_b64decode(text)


class WebAuthnJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return {'_bytes': webauthn_encode(o)}
        return super().default(o)


class WebAuthnAttestationView(WebAuthnView):
    def get(self, request, *args, **kwargs):
        challenge = os.urandom(32)
        request.session['webauthn_attest'] = webauthn_encode(challenge)
        data = webauthn.WebAuthnMakeCredentialOptions(
            challenge=challenge,
            rp_id=settings.WEBAUTHN_RP_ID,
            rp_name=settings.SITE_NAME,
            user_id=request.profile.webauthn_id,
            username=request.user.username,
            display_name=request.user.username,
            user_verification='discouraged',
            icon_url=gravatar(request.user.email),
            attestation='none',
        ).registration_dict
        data['excludeCredentials'] = [{
            'type': 'public-key',
            'id': credential.cred_id,
        } for credential in request.profile.webauthn_credentials.all()]
        return JsonResponse(data, encoder=WebAuthnJSONEncoder)

    def post(self, request, *args, **kwargs):
        if not request.session.get('webauthn_attest'):
            return HttpResponseBadRequest()

        if 'credential' not in request.POST or len(request.POST['credential']) > 65536:
            return HttpResponseBadRequest(_('Invalid WebAuthn response'))

        if 'name' not in request.POST or len(request.POST['name']) > 100:
            return HttpResponseBadRequest(_('Invalid name'))

        credential = json.loads(request.POST['credential'])

        response = webauthn.WebAuthnRegistrationResponse(
            rp_id=settings.WEBAUTHN_RP_ID,
            origin='https://' + request.get_host(),
            registration_response=credential['response'],
            challenge=request.session['webauthn_attest'],
            none_attestation_permitted=True,
        )

        try:
            credential = response.verify()
        except Exception as e:
            return HttpResponseBadRequest(str(e))

        model = WebAuthnCredential(
            user=request.profile, name=request.POST['name'],
            cred_id=credential.credential_id.decode('ascii'),
            public_key=credential.public_key.decode('ascii'),
            counter=credential.sign_count,
        )
        model.save()

        if not request.profile.is_webauthn_enabled:
            request.profile.is_webauthn_enabled = True
            request.profile.save(update_fields=['is_webauthn_enabled'])
        return HttpResponse('OK')


class TwoFactorLoginView(SuccessURLAllowedHostsMixin, TOTPView):
    title = _('Perform Two Factor Authentication')
    template_name = 'registration/two_factor_auth.html'

    def check_skip(self):
        return ((not self.profile.is_totp_enabled and not self.profile.is_webauthn_enabled) or
                self.request.session.get('2fa_passed', False))

    def next_page(self):
        redirect_to = self.request.GET.get('next', '')
        url_is_safe = is_safe_url(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return HttpResponseRedirect((redirect_to if url_is_safe else '') or reverse('user_page'))

    def form_valid(self, form):
        self.request.session['2fa_passed'] = True
        return self.next_page()
