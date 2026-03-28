from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0152_deactivate_user_permission'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='is_pinned',
            field=models.BooleanField(default=False, verbose_name='pinned'),
        ),
        migrations.AlterModelOptions(
            name='comment',
            options={
                'permissions': (('pin_comment', 'Pin comments'),),
                'verbose_name': 'comment',
                'verbose_name_plural': 'comments',
            },
        ),
    ]
