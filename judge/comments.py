from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Count, FilteredRelation, Q
from django.db.models.expressions import F, Value
from django.db.models.functions import Coalesce
from django.forms import ModelForm
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin
from reversion import revisions
from reversion.models import Revision, Version

from judge.dblock import LockModel
from judge.models import Comment, CommentLock
from judge.widgets import HeavyPreviewPageDownWidget


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['body', 'parent']
        widgets = {
            'parent': forms.HiddenInput(),
        }

        if HeavyPreviewPageDownWidget is not None:
            widgets['body'] = HeavyPreviewPageDownWidget(preview=reverse_lazy('comment_preview'),
                                                         preview_timeout=1000, hide_preview_button=True)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(CommentForm, self).__init__(*args, **kwargs)
        self.fields['body'].widget.attrs.update({'placeholder': _('Comment body')})

    def clean(self):
        if self.request is not None and self.request.user.is_authenticated:
            profile = self.request.profile
            if profile.mute:
                raise ValidationError(_('Your part is silent, little toad.'))
            elif not self.request.user.is_staff and not profile.has_any_solves:
                raise ValidationError(_('You must solve at least one problem before your voice can be heard.'))
        return super(CommentForm, self).clean()


class CommentedDetailView(TemplateResponseMixin, SingleObjectMixin, View):
    comment_page = None

    def get_comment_page(self):
        if self.comment_page is None:
            raise NotImplementedError()
        return self.comment_page

    def is_comment_locked(self):
        return (CommentLock.objects.filter(page=self.get_comment_page()).exists() and
                not self.request.user.has_perm('judge.override_comment_lock'))

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        page = self.get_comment_page()

        if self.is_comment_locked():
            return HttpResponseForbidden()

        parent = request.POST.get('parent')
        if parent:
            if len(parent) > 10:
                return HttpResponseBadRequest()
            try:
                parent = int(parent)
            except ValueError:
                return HttpResponseBadRequest()
            try:
                parent_comment = Comment.objects.get(hidden=False, id=parent, page=page)
            except Comment.DoesNotExist:
                return HttpResponseNotFound()
            if not (self.request.user.has_perm('judge.change_comment') or
                    parent_comment.time > timezone.now() - settings.DMOJ_COMMENT_REPLY_TIMEFRAME):
                return HttpResponseForbidden()

        form = CommentForm(request, request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.profile
            comment.page = page
            with LockModel(write=(Comment, Revision, Version), read=(ContentType,)), revisions.create_revision():
                revisions.set_user(request.user)
                revisions.set_comment(_('Posted comment'))
                comment.save()
            return HttpResponseRedirect(request.path)

        context = self.get_context_data(object=self.object, comment_form=form)
        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data(
            object=self.object,
            comment_form=CommentForm(request, initial={'page': self.get_comment_page(), 'parent': None}),
        ))

    def get_context_data(self, **kwargs):
        context = super(CommentedDetailView, self).get_context_data(**kwargs)
        queryset = Comment.objects.filter(hidden=False, page=self.get_comment_page())
        context['has_comments'] = queryset.exists()
        context['comment_lock'] = self.is_comment_locked()
        queryset = queryset.select_related('author__user').defer('author__about').annotate(revisions=Count('versions'))

        if self.request.user.is_authenticated:
            profile = self.request.profile
            queryset = queryset.annotate(
                my_vote=FilteredRelation('votes', condition=Q(votes__voter_id=profile.id)),
            ).annotate(vote_score=Coalesce(F('my_vote__score'), Value(0)))
            context['is_new_user'] = not self.request.user.is_staff and not profile.has_any_solves
        context['comment_list'] = queryset
        context['vote_hide_threshold'] = settings.DMOJ_COMMENT_VOTE_HIDE_THRESHOLD
        context['reply_cutoff'] = timezone.now() - settings.DMOJ_COMMENT_REPLY_TIMEFRAME

        return context
