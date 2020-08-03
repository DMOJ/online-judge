import hmac

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.translation import gettext as _
from django.views.generic import FormView
from peg_merge.forms import WCIPEGMergeActivationForm, WCIPEGMergeRequestForm

from judge.models import Comment, CommentVote, Profile, Submission
from judge.utils.views import TitleMixin, generic_message


class WCIPEGMergeRequest(LoginRequiredMixin, UserPassesTestMixin, TitleMixin, FormView):
    template_name = 'user/wcipeg-merge-request.html'
    form_class = WCIPEGMergeRequestForm

    def test_func(self):
        return self.request.profile.is_peg

    def get_title(self):
        return _('WCIPEG Merge Request')

    def form_valid(self, form):
        user = User.objects.get(username=form.cleaned_data['handle'])
        token = 'wcipeg_%d_%s' % (user.pk, self.request.user.email)
        hmac_token = hmac.new(force_bytes(settings.SECRET_KEY), msg=token.encode('utf-8'), digestmod='sha256')
        url = self.request.build_absolute_uri(reverse('wcipeg_merge_activate', args=[user.pk, hmac_token.hexdigest()]))
        form.send_email(url, user.email)
        return generic_message(self.request, _('Merge Requested'), _('Please click on the link sent to your email to '
                               'authorize the merge.'))


class WCIPEGMergeActivate(LoginRequiredMixin, UserPassesTestMixin, TitleMixin, FormView):
    template_name = 'user/wcipeg-merge-activate.html'
    form_class = WCIPEGMergeActivationForm

    def test_func(self):
        token = 'wcipeg_%s_%s' % (self.kwargs['pk'], self.request.user.email)
        hmac_token = hmac.new(force_bytes(settings.SECRET_KEY), msg=token.encode('utf-8'), digestmod='sha256')
        return hmac.compare_digest(hmac_token.hexdigest(), self.kwargs['token'])

    def merge(self, from_user, to_user):
        with transaction.atomic():
            from_user.peg_user.merge_into = to_user
            from_user.peg_user.save()
            Submission.objects.filter(user=from_user).update(user=to_user)
            Comment.objects.filter(author=from_user).update(author=to_user)
            CommentVote.objects.filter(voter=from_user).update(voter=to_user)
            user = from_user.user
            user.is_active = False
            user.save()

    def form_valid(self, form):
        self.merge(Profile.objects.get(user=self.request.user), Profile.objects.get(user__pk=self.kwargs['pk']))
        logout(self.request)
        return generic_message(self.request, _('Merge Successful'), _('Thanks! You can now login to your native DMOJ '
                               'account.'))

    def get_title(self):
        return _('WCIPEG Merge Activation')
