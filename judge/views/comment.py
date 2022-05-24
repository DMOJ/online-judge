from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import F
from django.forms.models import ModelForm
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, UpdateView
from reversion import revisions
from reversion.models import Version

from judge.dblock import LockModel
from judge.models import Comment, CommentVote
from judge.utils.views import TitleMixin
from judge.widgets import MathJaxPagedownWidget

__all__ = ['upvote_comment', 'downvote_comment', 'CommentEditAjax', 'CommentContent',
           'CommentEdit']


@login_required
def vote_comment(request, delta):
    if abs(delta) != 1:
        return HttpResponseBadRequest(_('Messing around, are we?'), content_type='text/plain')

    if request.method != 'POST':
        return HttpResponseForbidden()

    if 'id' not in request.POST or len(request.POST['id']) > 10:
        return HttpResponseBadRequest()

    if not request.user.is_staff and not request.profile.has_any_solves:
        return HttpResponseBadRequest(_('You must solve at least one problem before you can vote.'),
                                      content_type='text/plain')

    if request.profile.mute:
        return HttpResponseBadRequest(_('Your part is silent, little toad.'), content_type='text/plain')

    try:
        comment_id = int(request.POST['id'])
    except ValueError:
        return HttpResponseBadRequest()

    comment = Comment.objects.filter(id=comment_id, hidden=False).first()

    if not comment:
        return HttpResponseNotFound(_('Comment not found.'), content_type='text/plain')

    if comment.author == request.profile:
        return HttpResponseBadRequest(_('You cannot vote on your own comments.'), content_type='text/plain')

    vote = CommentVote()
    vote.comment_id = comment_id
    vote.voter = request.profile
    vote.score = delta

    while True:
        try:
            vote.save()
        except IntegrityError:
            with LockModel(write=(CommentVote,)):
                try:
                    vote = CommentVote.objects.get(comment_id=comment_id, voter=request.profile)
                except CommentVote.DoesNotExist:
                    # We must continue racing in case this is exploited to manipulate votes.
                    continue
                if -vote.score != delta:
                    return HttpResponseBadRequest(_('You already voted.'), content_type='text/plain')
                vote.delete()
            Comment.objects.filter(id=comment_id).update(score=F('score') - vote.score)
        else:
            Comment.objects.filter(id=comment_id).update(score=F('score') + delta)
        break
    return HttpResponse('success', content_type='text/plain')


def upvote_comment(request):
    return vote_comment(request, 1)


def downvote_comment(request):
    return vote_comment(request, -1)


class CommentMixin(object):
    model = Comment
    pk_url_kwarg = 'id'
    context_object_name = 'comment'

    def get_object(self, queryset=None):
        comment = super().get_object(queryset)
        if not comment.is_accessible_by(self.request.user):
            raise Http404()
        return comment


class CommentRevisionAjax(CommentMixin, DetailView):
    template_name = 'comments/revision-ajax.html'

    def get_context_data(self, **kwargs):
        context = super(CommentRevisionAjax, self).get_context_data(**kwargs)
        revisions = Version.objects.get_for_object(self.object).order_by('-revision')
        try:
            wanted = min(max(int(self.request.GET.get('revision', 0)), 0), len(revisions) - 1)
        except ValueError:
            raise Http404
        context['revision'] = revisions[wanted]
        return context

    def get_object(self, queryset=None):
        comment = super(CommentRevisionAjax, self).get_object(queryset)
        if comment.hidden and not self.request.user.has_perm('judge.change_comment'):
            raise Http404()
        return comment


class CommentEditForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        if MathJaxPagedownWidget is not None:
            widgets = {'body': MathJaxPagedownWidget(attrs={'id': 'id-edit-comment-body'})}


class CommentEditAjax(LoginRequiredMixin, CommentMixin, UpdateView):
    template_name = 'comments/edit-ajax.html'
    form_class = CommentEditForm

    def form_valid(self, form):
        with revisions.create_revision(atomic=True):
            revisions.set_comment(_('Edited from site'))
            revisions.set_user(self.request.user)
            return super(CommentEditAjax, self).form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_object(self, queryset=None):
        comment = super(CommentEditAjax, self).get_object(queryset)
        if self.request.user.has_perm('judge.change_comment'):
            return comment
        profile = self.request.profile
        if profile != comment.author or profile.mute or comment.hidden:
            raise Http404()
        return comment


class CommentEdit(TitleMixin, CommentEditAjax):
    template_name = 'comments/edit.html'

    def get_title(self):
        return _('Editing comment')


class CommentContent(CommentMixin, DetailView):
    template_name = 'comments/content.html'


class CommentVotesAjax(PermissionRequiredMixin, CommentMixin, DetailView):
    template_name = 'comments/votes.html'
    permission_required = 'judge.change_comment'

    def get_context_data(self, **kwargs):
        context = super(CommentVotesAjax, self).get_context_data(**kwargs)
        context['votes'] = (self.object.votes.select_related('voter__user')
                            .only('id', 'voter__display_rank', 'voter__user__username', 'score'))
        return context


@require_POST
def comment_hide(request):
    if not request.user.has_perm('judge.change_comment'):
        raise PermissionDenied()
    try:
        comment_id = int(request.POST['id'])
    except ValueError:
        return HttpResponseBadRequest()

    comment = get_object_or_404(Comment, id=comment_id)
    comment.get_descendants(include_self=True).update(hidden=True)
    return HttpResponse('ok')
