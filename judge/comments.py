from .models import Comment, Problem


def problem_comments(problem):
    return Comment.objects.filter(page='p:' + problem.code, parent=None)


def comment_form(request, page_id):
    from judge.forms import CommentForm
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user.profile
            comment.page = page_id
            comment.save()
        else:
            return form
    return CommentForm(initial={'page': page_id, 'parent': None})


def valid_comment_page(page):
    if page.startswith('p:'):
        if Problem.objects.filter(code=page[2:]).exists():
            return True
    return False
