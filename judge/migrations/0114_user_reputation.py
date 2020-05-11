from operator import mul

from django.conf import settings
from django.db import migrations, models


def update_reputation(apps, schema_editor):
    Comment = apps.get_model('judge', 'Comment')
    Profile = apps.get_model('judge', 'Profile')

    table = [pow(settings.DMOJ_REPUTATION_STEP, i) for i in range(settings.DMOJ_REPUTATION_ENTRIES)]
    authors = Profile.objects.filter(comment__isnull=False).distinct().defer('about')
    for p in authors:
        scores = (
            Comment.objects.filter(author=p, hidden=False).order_by('-time').values_list('score', flat=True)
        )
        entries = min(len(scores), len(table))
        p.reputation = sum(map(
            mul,
            table[:entries],
            map(settings.DMOJ_REPUTATION_FUNCTION, scores[:entries]),
        ))
    Profile.objects.bulk_update(authors, ['reputation'], batch_size=2000)


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0113_contest_decimal_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='reputation',
            field=models.FloatField(default=0),
        ),
        migrations.RunPython(update_reputation, migrations.RunPython.noop, atomic=True),
    ]
