from django.conf import settings
from django.contrib.syndication.views import Feed
from django.core.cache import cache
from django.utils import timezone
from django.utils.feedgenerator import Atom1Feed
from django.utils.html import format_html
from django.utils.http import urlquote

from judge.math_parser import MathHTMLParser, INLINE_MATH_PNG, DISPLAY_MATH_PNG
from judge.models import Comment, BlogPost, Problem
from judge.templatetags.latex_math import latex_math
from judge.utils.mathoid import MathoidMathParser
from judge.templatetags.markdown import markdown


class OldFeedMath(MathHTMLParser):
    def inline_math(self, math):
        return (r'<img class="tex-image" src="%s?\textstyle %s" alt="%s"/>' %
                (INLINE_MATH_PNG, urlquote(math), math))

    def display_math(self, math):
        return (r'<img class="tex-image" src="%s?\displaystyle %s" alt="%s"/>' %
                (DISPLAY_MATH_PNG, urlquote(math), math))


class MathoidFeedMath(MathoidMathParser):
    types = ('png',)

    def __init__(self):
        MathoidMathParser.__init__(self, 'png')

    def output_png(self, result):
        return format_html(u'<img src="{0}" style="{1}{3}" alt="{2}">',
                           result['png'], result['css'], result['tex'],
                           ['', 'display: block; margin: 0 auto'][result['display']])


class FeedMath(object):
    @classmethod
    def convert(cls, *args, **kwargs):
        if hasattr(settings, 'MATHOID_URL'):
            return MathoidFeedMath.convert(*args, **kwargs)
        else:
            return OldFeedMath.convert(*args, **kwargs)


class ProblemFeed(Feed):
    title = 'Recently added %s problems' % getattr(settings, 'SITE_NAME', 'DMOJ')
    link = '/'
    description = 'The latest problems added on the %s website' % getattr(settings, 'SITE_LONG_NAME', getattr(settings, 'SITE_NAME', 'DMOJ'))

    def items(self):
        return Problem.objects.filter(is_public=True).order_by('-date', '-id')[:25]

    def item_title(self, problem):
        return problem.name

    def item_description(self, problem):
        key = 'problem_feed:%d' % problem.id
        desc = cache.get(key)
        if desc is None:
            desc = unicode(FeedMath.convert(markdown(problem.description, 'problem'))[:500] + '...')
            cache.set(key, desc, 86400)
        return desc

    def item_pubdate(self, problem):
        return problem.date


class AtomProblemFeed(ProblemFeed):
    feed_type = Atom1Feed
    subtitle = ProblemFeed.description


class CommentFeed(Feed):
    title = 'Latest %s comments' % getattr(settings, 'SITE_NAME', 'DMOJ')
    link = '/'
    description = 'The latest comments on the %s website' % getattr(settings, 'SITE_LONG_NAME', getattr(settings, 'SITE_NAME', 'DMOJ'))

    def items(self):
        return Comment.objects.filter(hidden=False).order_by('-time')[:25]

    def item_title(self, comment):
        return '%s -> %s' % (comment.author.user.username,
                             comment.parent.title if comment.parent is not None else comment.page_title)

    def item_description(self, comment):
        key = 'comment_feed:%d' % comment.id
        desc = cache.get(key)
        if desc is None:
            desc = unicode(FeedMath.convert(markdown(comment.body, 'comment')))
            cache.set(key, desc, 86400)
        return desc

    def item_pubdate(self, comment):
        return comment.time


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
            summary = unicode(latex_math(FeedMath.convert(markdown(post.summary or post.content, 'blog'))))
            cache.set(key, summary, 86400)
        return summary

    def item_pubdate(self, post):
        return post.publish_on


class AtomBlogFeed(CommentFeed):
    feed_type = Atom1Feed
    subtitle = BlogFeed.description
