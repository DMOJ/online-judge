from django.db import migrations
from django.db.models import F, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce


def delete_self_votes(apps, schema_editor):
    Comment = apps.get_model('judge', 'Comment')
    CommentVote = apps.get_model('judge', 'CommentVote')

    CommentVote.objects.filter(voter=F('comment__author')).delete()
    Comment.objects.update(
        score=Subquery(
            Comment.objects.filter(
                id=OuterRef('id'),
            ).order_by().annotate(
                newscore=Coalesce(Sum('votes__score'), 0),
            ).values('newscore'),
        ),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0131_spectate_contests'),
    ]

    operations = [
        migrations.RunPython(delete_self_votes, migrations.RunPython.noop),
    ]
