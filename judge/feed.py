from django.contrib.syndication.views import Feed
from django.utils import timezone
from django.utils.feedgenerator import Atom1Feed
from judge.models import Comment, BlogPost


class CommentFeed(Feed):
    title = 'Latest DMOJ comments'
    link = '/'
    description = 'The latest comments on the Don Mills Online Judge website'

    def items(self):
        return Comment.objects.order_by('-time')[:25]

    def item_title(self, comment):
        return '%s -> %s' % (comment.author.long_display_name,
                             comment.parent.title if comment.parent is not None else comment.page_title)

    def item_description(self, comment):
        return comment.body


class AtomCommentFeed(CommentFeed):
    feed_type = Atom1Feed
    subtitle = CommentFeed.description


class BlogFeed(Feed):
    title = 'Latest DMOJ Blog Posts'
    link = '/'
    description = 'The latest blog posts from the Don Mills Online Judge'

    def items(self):
        return BlogPost.objects.filter(visible=True, publish_on__lte=timezone.now()).order_by('-sticky', '-publish_on')

    def item_title(self, post):
        return post.title

    def item_description(self, post):
        return post.summary or post.content


class AtomBlogFeed(CommentFeed):
    feed_type = Atom1Feed
    subtitle = BlogFeed.description