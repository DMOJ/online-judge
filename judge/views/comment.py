from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import IntegrityError, transaction
from django.forms.models import ModelForm
from django.http import HttpResponseForbidden, HttpResponseBadRequest, HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, UpdateView
from reversion import revisions
from reversion.models import Version

from judge.models import Comment, CommentVote
from judge.utils.views import TitleMixin
from judge.widgets import MathJaxPagedownWidget

__all__ = ['upvote_comment', 'downvote_comment', 'CommentHistoryAjax', 'CommentEditAjax', 'CommentContent',
           'CommentEdit', 'CommentHistory']


@login_required
def vote_comment(request, delta):
    if abs(delta) != 1:
        return HttpResponseBadRequest(_('Messing around, are we?'), content_type='text/plain')

    if request.method != 'POST':
        return HttpResponseForbidden()

    if 'id' not in request.POST:
        return HttpResponseBadRequest()

    comment = get_object_or_404(Comment, id=request.POST['id'])

    vote = CommentVote()
    vote.comment = comment
    vote.voter = request.user.profile
    vote.score = delta

    try:
        vote.save()
    except IntegrityError:
        vote = CommentVote.objects.get(comment=comment, voter=request.user.profile)
        if -vote.score == delta:
            comment.score -= vote.score
            comment.save()
            vote.delete()
        else:
            return HttpResponseBadRequest(_('You already voted.'), content_type='text/plain')
    else:
        comment.score += delta
        comment.save()
    return HttpResponse('success', content_type='text/plain')


def upvote_comment(request):
    return vote_comment(request, 1)


def downvote_comment(request):
    return vote_comment(request, -1)


class CommentMixin(object):
    model = Comment
    pk_url_kwarg = 'id'
    context_object_name = 'comment'


class CommentRevisionAjax(CommentMixin, DetailView):
    template_name = 'comments/revision-ajax.jade'

    def get_context_data(self, **kwargs):
        context = super(CommentRevisionAjax, self).get_context_data(**kwargs)
        revisions = Version.objects.get_for_object(self.object)
        wanted = self.request.GET.get('revision', None)
        context['revision'] = revisions.get(wanted)
        return context

    def get_object(self, queryset=None):
        comment = super(CommentRevisionAjax, self).get_object(queryset)
        if comment.hidden and not self.request.user.has_perm('judge.change_comment'):
            raise Http404()
        return comment


class CommentHistoryAjax(CommentMixin, DetailView):
    template_name = 'comments/history-ajax.jade'

    def get_context_data(self, **kwargs):
        context = super(CommentHistoryAjax, self).get_context_data(**kwargs)
        context['revisions'] = Version.objects.get_for_object(self.object)
        return context

    def get_object(self, queryset=None):
        comment = super(CommentHistoryAjax, self).get_object(queryset)
        if comment.hidden and not self.request.user.has_perm('judge.change_comment'):
            raise Http404()
        return comment


class CommentHistory(TitleMixin, CommentHistoryAjax):
    template_name = 'comments/history.jade'

    def get_title(self):
        return _('Revisions for %s') % self.object.title


class CommentEditForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['title', 'body']
        if MathJaxPagedownWidget is not None:
            widgets = {'body': MathJaxPagedownWidget(attrs={'id': 'id-edit-comment-body'})}


class CommentEditAjax(LoginRequiredMixin, CommentMixin, UpdateView):
    template_name = 'comments/edit-ajax.jade'
    form_class = CommentEditForm

    def form_valid(self, form):
        with transaction.atomic(), revisions.create_revision():
            revisions.set_comment(_('Edited from site'))
            revisions.set_user(self.request.user)
            return super(CommentEditAjax, self).form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_object(self, queryset=None):
        comment = super(CommentEditAjax, self).get_object(queryset)
        if self.request.user.has_perm('judge.change_comment'):
            return comment
        profile = self.request.user.profile
        if profile != comment.author or profile.mute or comment.hidden:
            raise Http404()
        return comment


class CommentEdit(TitleMixin, CommentEditAjax):
    template_name = 'comments/edit.jade'

    def get_title(self):
        return _('Editing %s') % self.object.title


class CommentContent(CommentMixin, DetailView):
    template_name = 'comments/content.jade'


class CommentVotesAjax(PermissionRequiredMixin, CommentMixin, DetailView):
    template_name = 'comments/votes.jade'
    permission_required = 'judge.change_commentvote'

    def get_context_data(self, **kwargs):
        context = super(CommentVotesAjax, self).get_context_data(**kwargs)
        context['votes'] = (self.object.votes.select_related('voter__user')
                            .only('id', 'voter__display_rank', 'voter__user__username', 'score'))
        return context
