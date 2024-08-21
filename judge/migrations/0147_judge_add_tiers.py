from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('judge', '0146_comment_revision_count_v2'),
    ]

    operations = [
        migrations.AddField(
            model_name='judge',
            name='tier',
            field=models.PositiveIntegerField(
                default=1,
                help_text='The tier of this judge. Only online judges of the minimum tier will be used. This is used for high-availability.',
                verbose_name='judge tier',
            ),
        ),
    ]
