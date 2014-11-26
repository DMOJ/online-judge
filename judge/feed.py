from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from judge.models import Comment


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