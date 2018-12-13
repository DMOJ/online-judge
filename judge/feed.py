from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.syndication.views import Feed
from django.core.cache import cache
from django.utils import timezone
from django.utils.feedgenerator import Atom1Feed

from judge.jinja2.markdown import markdown
from judge.models import Comment, BlogPost, Problem


class ProblemFeed(Feed):
    title = 'Recently Added %s Problems' % getattr(settings, 'SITE_NAME', 'DMOJ')
    link = '/'
    description = 'The latest problems added on the %s website' % getattr(settings, 'SITE_LONG_NAME', getattr(settings, 'SITE_NAME', 'DMOJ'))

    def items(self):
        return Problem.objects.filter(is_public=True, is_organization_private=False).order_by('-date', '-id')[:25]

    def item_title(self, problem):
        return problem.name

    def item_description(self, problem):
        key = 'problem_feed:%d' % problem.id
        desc = cache.get(key)
        if desc is None:
            desc = unicode(markdown(problem.description, 'problem'))[:500] + '...'
            cache.set(key, desc, 86400)
        return desc

    def item_pubdate(self, problem):
        return problem.date

    item_updateddate = item_pubdate


class AtomProblemFeed(ProblemFeed):
    feed_type = Atom1Feed
    subtitle = ProblemFeed.description


class CommentFeed(Feed):
    title = 'Latest %s Comments' % getattr(settings, 'SITE_NAME', 'DMOJ')
    link = '/'
    description = 'The latest comments on the %s website' % getattr(settings, 'SITE_LONG_NAME', getattr(settings, 'SITE_NAME', 'DMOJ'))

    def items(self):
        return Comment.most_recent(AnonymousUser(), 25)

    def item_title(self, comment):
        return '%s -> %s' % (comment.author.user.username, comment.page_title)

    def item_description(self, comment):
        key = 'comment_feed:%d' % comment.id
        desc = cache.get(key)
        if desc is None:
            desc = unicode(markdown(comment.body, 'comment'))
            cache.set(key, desc, 86400)
        return desc

    def item_pubdate(self, comment):
        return comment.time

    item_updateddate = item_pubdate


class AtomCommentFeed(CommentFeed):
    feed_type = Atom1Feed
    subtitle = CommentFeed.description


class BlogFeed(Feed):
    title = 'Latest %s Blog Posts' % getattr(settings, 'SITE_NAME', 'DMOJ')
    link = '/'
    description = 'The latest blog posts from the %s' % getattr(settings, 'SITE_LONG_NAME', getattr(settings, 'SITE_NAME', 'DMOJ'))

    def items(self):
        return BlogPost.objects.filter(visible=True, publish_on__lte=timezone.now()).order_by('-sticky', '-publish_on')

    def item_title(self, post):
        return post.title

    def item_description(self, post):
        key = 'blog_feed:%d' % post.id
        summary = cache.get(key)
        if summary is None:
            summary = unicode(markdown(post.summary or post.content, 'blog'))
            cache.set(key, summary, 86400)
        return summary

    def item_pubdate(self, post):
        return post.publish_on

    item_updateddate = item_pubdate


class AtomBlogFeed(BlogFeed):
    feed_type = Atom1Feed
    subtitle = BlogFeed.description
