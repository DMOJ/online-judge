from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.forms import ModelForm
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin
from reversion import revisions
from reversion.models import Revision, Version

from judge.dblock import LockModel
from judge.models import Comment, Profile
from judge.widgets import MathJaxPagedownWidget, PagedownWidget


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['title', 'body', 'parent']
        widgets = {
            'parent': forms.HiddenInput(),
        }
        if PagedownWidget is not None:
            widgets['body'] = MathJaxPagedownWidget(load_math=False)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(CommentForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'placeholder': 'Comment title'})
        self.fields['body'].widget.attrs.update({'placeholder': 'Comment body'})

    def clean(self):
        if self.request is not None and self.request.user.is_authenticated() and self.request.user.profile.mute:
            raise ValidationError('You are not allowed to comment...')
        return super(CommentForm, self).clean()


class CommentedDetailView(TemplateResponseMixin, SingleObjectMixin, View):
    comment_page = None

    def get_comment_page(self):
        if self.comment_page is None:
            raise NotImplementedError()
        return self.comment_page

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        page = self.get_comment_page()

        with LockModel(write=(Comment, Revision, Version), read=(Profile, ContentType)):
            form = CommentForm(request, request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.author = request.user.profile
                comment.page = page
                with revisions.create_revision():
                    revisions.set_user(request.user)
                    revisions.set_comment('Posted comment')
                    comment.save()
                return HttpResponseRedirect(request.path)

        context = self.get_context_data(object=self.object, comment_form=form)
        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data(
            object=self.object,
            comment_form=CommentForm(request, initial={'page': self.get_comment_page(), 'parent': None})
        ))

    def get_context_data(self, **kwargs):
        context = super(CommentedDetailView, self).get_context_data(**kwargs)
        queryset = Comment.objects.filter(page=self.get_comment_page())
        context['has_comments'] = queryset.exists()
        context['comment_list'] = queryset.select_related('author__user').defer('author__about') \
                                          .annotate(revisions=Count('versions'))
        return context
