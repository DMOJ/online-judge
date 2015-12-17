from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from django.views.generic import ListView

from judge.comments import CommentedDetailView
from judge.models import BlogPost, Comment, Problem, Contest
from judge.utils.diggpaginator import DiggPaginator
from judge.utils.views import TitleMixin


class PostList(ListView):
    model = BlogPost
    paginate_by = 10
    context_object_name = 'posts'
    template_name = 'blog/list.jade'
    title = None

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        return DiggPaginator(queryset, per_page, body=6, padding=2,
                             orphans=orphans, allow_empty_first_page=allow_empty_first_page, **kwargs)

    def get_queryset(self):
        return BlogPost.objects.filter(visible=True, publish_on__lte=timezone.now()).order_by('-sticky', '-publish_on')

    def get_context_data(self, **kwargs):
        context = super(PostList, self).get_context_data(**kwargs)
        context['title'] = self.title or 'Page %d of Posts' % context['page_obj'].number
        context['first_page_href'] = reverse('home')
        context['page_prefix'] = reverse('blog_post_list')
        context['comments'] = Comment.objects.filter(hidden=False).select_related('author__user').defer('author__about').order_by('-id')[:10]
        context['problems'] = Problem.objects.filter(is_public=True).order_by('-date', '-id')[:7]
        now = timezone.now()

        visible_contests = Contest.objects.filter(is_public=True)
        q = Q(is_private=False)
        if self.request.user.is_authenticated():
            q |= Q(organizations__in=self.request.user.profile.organizations.all())
        visible_contests = visible_contests.filter(q)
        context['current_contests'] = visible_contests.filter(start_time__lte=now, end_time__gt=now)
        context['future_contests'] = visible_contests.filter(start_time__gt=now)
        return context


class PostView(TitleMixin, CommentedDetailView):
    model = BlogPost
    pk_url_kwarg = 'id'
    context_object_name = 'post'
    template_name = 'blog/content.jade'

    def get_title(self):
        return self.object.title

    def get_comment_page(self):
        return 'b:%s' % self.object.id

    def get_object(self, queryset=None):
        post = super(PostView, self).get_object(queryset)
        if (not post.visible or post.publish_on > timezone.now())\
                and not self.request.user.has_perm('judge.see_hidden_post'):
            raise Http404()
        return post
