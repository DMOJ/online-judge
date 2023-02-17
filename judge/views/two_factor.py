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
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils.http import is_safe_url
from django.utils.translation import gettext as _, gettext_lazy
from django.views.generic import FormView, View
from django.views.generic.base import ContextMixin
from django.views.generic.detail import SingleObjectMixin

from judge.forms import TOTPEnableForm, TOTPForm, TwoFactorLoginForm
from judge.jinja2.gravatar import gravatar
from judge.models import WebAuthnCredential
from judge.utils.two_factor import WebAuthnJSONEncoder, webauthn_encode
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
    title = gettext_lazy('Enable Two-factor Authentication')
    form_class = TOTPEnableForm
    template_name = 'registration/totp_enable.html'
    is_refresh = False

    def get(self, request, *args, **kwargs):
        profile = self.profile
        if 'totp_enable_key' not in request.session:
            request.session['totp_enable_key'] = pyotp.random_base32(length=32)
        if not profile.scratch_codes:
            profile.generate_scratch_codes()
        return self.render_to_response(self.get_context_data())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['totp_key'] = self.request.session['totp_enable_key']
        return kwargs

    def check_skip(self):
        return self.profile.is_totp_enabled

    def post(self, request, *args, **kwargs):
        if not request.session['totp_enable_key']:
            return HttpResponseBadRequest('No TOTP key generated on server side?')
        return super(TOTPEnableView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TOTPEnableView, self).get_context_data(**kwargs)
        context['totp_key'] = self.request.session['totp_enable_key']
        context['scratch_codes'] = [] if self.is_refresh else json.loads(self.profile.scratch_codes)
        context['qr_code'] = self.render_qr_code(self.request.user.username, context['totp_key'])
        context['is_refresh'] = self.is_refresh
        context['is_hardcore'] = settings.DMOJ_2FA_HARDCORE
        return context

    def form_valid(self, form):
        self.profile.is_totp_enabled = True
        self.profile.totp_key = self.request.session['totp_enable_key']
        self.profile.save(update_fields=['is_totp_enabled', 'totp_key'])
        # Make sure users don't get prompted to enter code right after enabling
        self.request.session['2fa_passed'] = True
        del self.request.session['totp_enable_key']
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


class TOTPRefreshView(TOTPEnableView):
    title = gettext_lazy('Refresh Two-factor Authentication')
    is_refresh = True

    def check_skip(self):
        return not self.profile.is_totp_enabled


class TOTPDisableView(TOTPView):
    title = gettext_lazy('Disable Two-factor Authentication')
    template_name = 'registration/totp_disable.html'

    def check_skip(self):
        if not self.profile.is_totp_enabled:
            return True
        return settings.DMOJ_REQUIRE_STAFF_2FA and self.request.user.is_staff and not self.profile.is_webauthn_enabled

    def form_valid(self, form):
        self.profile.is_totp_enabled = False
        self.profile.totp_key = None
        self.profile.scratch_codes = None
        self.profile.save()
        return self.next_page()


class WebAuthnView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not settings.WEBAUTHN_RP_ID:
            raise Http404()
        return super(WebAuthnView, self).dispatch(request, *args, **kwargs)


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
            'id': {'_bytes': credential.cred_id},
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


class WebAuthnAttestView(WebAuthnView):
    def get(self, request, *args, **kwargs):
        challenge = os.urandom(32)
        request.session['webauthn_assert'] = webauthn_encode(challenge)
        data = webauthn.WebAuthnAssertionOptions(
            [credential.webauthn_user for credential in
             request.profile.webauthn_credentials.select_related('user__user')],
            challenge,
        ).assertion_dict
        return JsonResponse(data, encoder=WebAuthnJSONEncoder)


class WebAuthnDeleteView(SingleObjectMixin, WebAuthnView):
    def get_queryset(self):
        return self.request.profile.webauthn_credentials.all()

    def post(self, request, *args, **kwargs):
        credential = self.get_object()
        count = self.get_queryset().count()

        if settings.DMOJ_REQUIRE_STAFF_2FA and self.request.user.is_staff and \
                count <= 1 and not request.profile.is_totp_enabled:
            return HttpResponseBadRequest(_('Staff may not disable 2FA'))
        credential.delete()

        return HttpResponse()


class TwoFactorLoginView(SuccessURLAllowedHostsMixin, TOTPView, ContextMixin):
    form_class = TwoFactorLoginForm
    title = gettext_lazy('Perform Two-factor Authentication')
    template_name = 'registration/two_factor_auth.html'
    extra_context = {'tfa_in_progress': True}

    def get_form_kwargs(self):
        result = super().get_form_kwargs()
        result['webauthn_challenge'] = self.request.session.get('webauthn_assert')
        result['webauthn_origin'] = 'https://' + self.request.get_host()
        return result

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_hardcore'] = settings.DMOJ_2FA_HARDCORE
        return context
