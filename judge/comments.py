from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.views.generic import DetailView, View
from django.views.generic.detail import SingleObjectMixin
from .models import Comment, Problem


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['title', 'body', 'parent']
        widgets = {
            'parent': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(CommentForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'style': 'min-width:100%', 'placeholder': 'Comment title'})
        self.fields['body'].widget.attrs.update({'style': 'min-width:100%', 'placeholder': 'Comment body'})

    def clean_page(self):
        page = self.cleaned_data['page']
        if not valid_comment_page(page):
            raise ValidationError('Invalid page id: %(id)s', params={'id': page})


class CommentedDetailView(SingleObjectMixin, View):
    comment_page = None

    def get_comment_page(self):
        if self.comment_page is None:
            raise NotImplementedError()
        return self.comment_page

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user.profile
            comment.page = self.get_comment_page()
            comment.save()
            return

        context = self.get_context_data(object=self.object, comment_form=form)
        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data(
            object=self.object,
            comment_form=CommentForm(initial={'page': self.get_comment_page(), 'parent': None})
        ))

    def get_context_data(self, **kwargs):
        context = super(CommentedDetailView, self).get_context_data(**kwargs)
        context['commend_list'] = Comment.objects.filter(page=self.get_comment_page(), parent=None)
        return context


def problem_comments(problem):
    return Comment.objects.filter(page='p:' + problem.code, parent=None)


def contest_comments(contest):
    return Comment.objects.filter(page='c:' + contest.key, parent=None)


def comment_form(request, page_id):
    from judge.forms import CommentForm
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user.profile
            comment.page = page_id
            comment.save()
            return
        else:
            return form
    return CommentForm(initial={'page': page_id, 'parent': None})


def valid_comment_page(page):
    if page.startswith('p:'):
        if Problem.objects.filter(code=page[2:]).exists():
            return True
    return False
