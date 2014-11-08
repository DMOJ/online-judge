from django.http import HttpResponseForbidden, HttpResponseRedirect
from .models import Comment, Problem


class CommentMixin(object):
    def get_page_id(self):
        raise NotImplementedError()

    def get_success_url(self):
        return self.request.path

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.author = self.request.user.profile
        comment.page = self.get_page_id()
        comment.save()
        return super(CommentMixin, self).form_valid(form)

    def post(self, request, *args, **kwargs):
        from judge.forms import CommentForm
        if not request.user.is_authenticated():
            return HttpResponseForbidden()

        self.comment_form = form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user.profile
            comment.page = self.get_page_id()
            comment.save()
            return HttpResponseRedirect(request.path)

    def get_context_data(self, **kwargs):
        context = super(CommentMixin, self).get_context_data(**kwargs)
        context['comment_list'] = Comment.objects.filter(page=self.get_page_id(), parent=None)
        context['comment_form'] = self.comment_form
        return context

    def get(self, request, *args, **kwargs):
        from judge.forms import CommentForm
        self.comment_form = CommentForm(initial={'page': self.get_page_id(), 'parent': None})


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
