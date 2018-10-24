import base64
from io import BytesIO

import pyotp
import qrcode
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views.generic import FormView

from judge.forms import TOTPForm
from judge.utils.views import TitleMixin


class TOTPView(TitleMixin, LoginRequiredMixin, FormView):
    form_class = TOTPForm

    def get_form_kwargs(self):
        result = super(TOTPView, self).get_form_kwargs()
        result['totp_key'] = self.profile.totp_key
        return result

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.profile = request.user.profile
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
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue())


class TOTPDisableView(TOTPView):
    title = _('Disable Two Factor Authentication')
    template_name = 'registration/totp_disable.html'

    def check_skip(self):
        return not self.profile.is_totp_enabled

    def form_valid(self, form):
        self.profile.is_totp_enabled = False
        self.profile.totp_key = None
        self.profile.save()
        return self.next_page()


class TOTPLoginView(TOTPView):
    title = _('Perform Two Factor Authetication')
    template_name = 'registration/totp_auth.html'

    def check_skip(self):
        return not self.profile.is_totp_enabled or self.request.session.get('2fa_passed', False)

    def next_page(self):
        return HttpResponseRedirect(self.request.GET.get('next', '') or reverse('user_page'))

    def form_valid(self, form):
        self.request.session['2fa_passed'] = True
        return self.next_page()
