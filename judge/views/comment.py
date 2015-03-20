from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import IntegrityError, transaction
from django.http import HttpResponseForbidden, HttpResponseBadRequest, HttpResponse, Http404
from django.views.generic import DetailView, UpdateView
import reversion

from judge.models import Comment, CommentVote
from judge.utils.views import LoginRequiredMixin


__all__ = ['upvote_comment', 'downvote_comment', 'CommentHistory', 'CommentEdit', 'CommentEditDone']


@login_required
def vote_comment(request, delta):
    assert abs(delta) == 1

    if request.method != 'POST':
        return HttpResponseForbidden()

    if 'id' not in request.POST:
        return HttpResponseBadRequest()

    comment = Comment.objects.get(id=request.POST['id'])

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
            return HttpResponseBadRequest('You already voted.', mimetype='text/plain')
    else:
        comment.score += delta
        comment.save()
    return HttpResponse('success', mimetype='text/plain')


def upvote_comment(request):
    return vote_comment(request, 1)


def downvote_comment(request):
    return vote_comment(request, -1)


class CommentHistory(DetailView):
    model = Comment
    pk_url_kwarg = 'id'
    context_object_name = 'comment'
    template_name = 'comments/history.jade'

    def get_context_data(self, **kwargs):
        context = super(CommentHistory, self).get_context_data(**kwargs)
        context['revisions'] = reversion.get_for_object(self.object)
        return context


class CommentEdit(LoginRequiredMixin, UpdateView):
    model = Comment
    pk_url_kwarg = 'id'
    context_object_name = 'comment'
    template_name = 'comments/edit.jade'
    fields = ['title', 'body']

    def form_valid(self, form):
        with transaction.atomic(), reversion.create_revision():
            reversion.set_comment('Edited from site')
            reversion.set_user(self.request.user)
            return super(CommentEdit, self).form_valid(form)

    def get_success_url(self):
        return reverse('comment_edit_done', args=(self.object.id,))

    def get_object(self, queryset=None):
        comment = super(CommentEdit, self).get_object(queryset)
        if self.request.user.has_perm('judge.change_comment'):
            return comment
        profile = self.request.user.profile
        if profile != comment.author or profile.mute:
            raise Http404()
        return comment


class CommentEditDone(DetailView):
    model = Comment
    pk_url_kwarg = 'id'
    context_object_name = 'comment'
    template_name = 'comments/closebox.jade'