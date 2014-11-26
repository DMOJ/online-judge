from django.contrib.syndication.views import Feed
from judge.models import Comment


class CommentFeed(Feed):
    title = 'Lates DMOJ comments'
    link = '/'
    description = 'The latest comments on the Don Mills Online Judge website'

    def items(self):
        return Comment.objects.order_by('-time')[:25]

    def item_title(self, comment):
        return '%s -> %s' % (comment.author.long_display_name,
                             comment.parent.title if comment.parent is not None else comment.page_title)

    def item_description(self, comment):
        return comment.body