from django.conf import settings
from django.db.models import Count, Max
from datetime import datetime

from django.forms import ModelForm, ValidationError
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from reversion.models import Revision, Version
from django.utils import timezone

from django.utils.translation import gettext as _
from django.views.generic import ListView
from django.template import loader
from django.contrib.contenttypes.models import ContentType
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic import View
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin
from judge.comments import CommentedDetailView
from judge.dblock import LockModel
from judge.models import BlogPost, Comment, Contest, Language, Problem, ProblemClarification, Profile, Submission, \
    Ticket
from judge.utils.cachedict import CacheDict
from judge.utils.diggpaginator import DiggPaginator
from judge.utils.opengraph import generate_opengraph
from judge.utils.tickets import filter_visible_tickets
from judge.utils.views import TitleMixin
from reversion import revisions

from judge.widgets.pagedown import HeavyPreviewPageDownWidget


class PostList(ListView):
    model = BlogPost
    paginate_by = 10
    context_object_name = 'posts'
    template_name = 'blog/list.html'
    title = None

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        return DiggPaginator(queryset, per_page, body=6, padding=2,
                             orphans=orphans, allow_empty_first_page=allow_empty_first_page, **kwargs)

    def get_queryset(self):
        return (BlogPost.objects.filter(visible=True, publish_on__lte=timezone.now()).order_by('-sticky', '-publish_on')
                .prefetch_related('authors__user'))

    def get_context_data(self, **kwargs):
        context = super(PostList, self).get_context_data(**kwargs)
        context['title'] = self.title or _('Page %d of Posts') % context['page_obj'].number
        context['first_page_href'] = reverse('home')
        context['page_prefix'] = reverse('blog_post_list')
        context['comments'] = Comment.most_recent(self.request.user, 10)
        context['new_problems'] = Problem.get_public_problems() \
                                         .order_by('-date', 'code')[:settings.DMOJ_BLOG_NEW_PROBLEM_COUNT]
        context['page_titles'] = CacheDict(lambda page: Comment.get_page_title(page))

        context['has_clarifications'] = False
        if self.request.user.is_authenticated:
            participation = self.request.profile.current_contest
            if participation:
                clarifications = ProblemClarification.objects.filter(problem__in=participation.contest.problems.all())
                context['has_clarifications'] = clarifications.count() > 0
                context['clarifications'] = clarifications.order_by('-date')

        context['user_count'] = Profile.objects.count
        context['problem_count'] = Problem.get_public_problems().count
        context['submission_count'] = lambda: Submission.objects.aggregate(max_id=Max('id'))['max_id'] or 0
        context['language_count'] = Language.objects.count

        context['post_comment_counts'] = {
            int(page[2:]): count for page, count in
            Comment.objects
                   .filter(page__in=['b:%d' % post.id for post in context['posts']], hidden=False)
                   .values_list('page').annotate(count=Count('page')).order_by()
        }

        now = timezone.now()

        visible_contests = Contest.get_visible_contests(self.request.user).filter(is_visible=True) \
                                  .order_by('start_time')

        context['current_contests'] = visible_contests.filter(start_time__lte=now, end_time__gt=now)
        context['future_contests'] = visible_contests.filter(start_time__gt=now)

        if self.request.user.is_authenticated:
            context['own_open_tickets'] = (
                Ticket.objects.filter(user=self.request.profile, is_open=True).order_by('-id')
                              .prefetch_related('linked_item').select_related('user__user')
            )
        else:
            context['own_open_tickets'] = []

        # Superusers better be staffs, not the spell-casting kind either.
        if self.request.user.is_staff:
            tickets = (Ticket.objects.order_by('-id').filter(is_open=True).prefetch_related('linked_item')
                             .select_related('user__user'))
            context['open_tickets'] = filter_visible_tickets(tickets, self.request.user)[:10]
        else:
            context['open_tickets'] = []
        return context


class PostView(TitleMixin, CommentedDetailView):
    model = BlogPost
    pk_url_kwarg = 'id'
    context_object_name = 'post'
    template_name = 'blog/content.html'

    def get_title(self):
        return self.object.title

    def get_comment_page(self):
        return 'b:%s' % self.object.id

    def get_context_data(self, **kwargs):
        context = super(PostView, self).get_context_data(**kwargs)

        metadata = generate_opengraph('generated-meta-blog:%d' % self.object.id,
                                      self.object.summary or self.object.content, 'blog')
        context['meta_description'] = metadata[0]
        context['og_image'] = self.object.og_image or metadata[1]

        return context

    def get_object(self, queryset=None):
        post = super(PostView, self).get_object(queryset)
        
        print(self.request.user)
        if not post.can_see(self.request.user):
            raise Http404()
        return post

class PostForm(ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'slug', 'content', 'summary', ]
        
        widgets = {}
        if HeavyPreviewPageDownWidget is not None:
            widgets['content'] = HeavyPreviewPageDownWidget(preview=reverse_lazy('blog_preview'),
                                                         preview_timeout=1000, hide_preview_button=True)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['content'].widget.attrs.update({'placeholder': _('Post content')})


    def clean(self):
        if self.request is not None and self.request.user.is_authenticated:
            profile = self.request.profile
            if profile.mute:
                raise ValidationError(_('Your part is silent, little toad.'))
            elif not self.request.user.is_staff and not profile.has_any_solves:
                raise ValidationError(_('You must solve at least one problem before your voice can be heard.'))
        return super(PostForm, self).clean()
    
class NewPostView(TemplateResponseMixin, SingleObjectMixin, View):
    model = BlogPost
    pk_url_kwarg = 'id'
    context_object_name = 'post'
    template_name = 'blog/new.html'
    
    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        self.object = None

        form = PostForm(request, request.POST)
        print(form)
        print(f"Valid {form.is_valid()}")
        if form.is_valid():
            post = form.save(commit=False)
            
            with LockModel(write=(BlogPost, Revision, Version, "judge_blogpost_authors"), read=(ContentType, Profile,)), revisions.create_revision():
                post.publish_on = datetime.now()
                post.save()
                post.authors.add(request.profile)
                revisions.set_user(request.user)
                revisions.set_comment(_('Posted post'))
                post.save()
            return HttpResponseRedirect(request.path)

        context = self.get_context_data(object=self.object, blog_form=form)
        return self.render_to_response(context)

    def get_title(self):
        return "New post"

    def get(self, request, *args, **kwargs):
        # self.object = self.get_object()
        self.object = None
        return render(request, 'blog/new.html', {'blog_form': PostForm(request)})
        return self.render_to_response({ 'form': PostForm() })

    def get_context_data(self, **kwargs):
        profile = self.request.profile
        context = super(NewPostView, self).get_context_data(**kwargs)
        
        context["blog_form"] = {
                "errors": None, 
                "content": "" 
            }
        context['title'] = self.get_title()

        if self.request.user.is_authenticated:
            context['is_new_user'] = not self.request.user.is_staff and not profile.has_any_solves
            
        
        # context = super(CommentedDetailView, self).get_context_data(**kwargs)
        # queryset = Comment.objects.filter(hidden=False, page=self.get_comment_page())
        # context['has_comments'] = queryset.exists()
        # context['comment_lock'] = self.is_comment_locked()
        # queryset = queryset.select_related('author__user').defer('author__about')

        # if self.request.user.is_authenticated:
        #     profile = self.request.profile
        #     queryset = queryset.annotate(
        #         my_vote=FilteredRelation('votes', condition=Q(votes__voter_id=profile.id)),
        #     ).annotate(vote_score=Coalesce(F('my_vote__score'), Value(0)))
        #     context['is_new_user'] = not self.request.user.is_staff and not profile.has_any_solves
        # context['comment_list'] = queryset
        # context['vote_hide_threshold'] = settings.DMOJ_COMMENT_VOTE_HIDE_THRESHOLD
        # context['reply_cutoff'] = timezone.now() - settings.DMOJ_COMMENT_REPLY_TIMEFRAME

        return context
    