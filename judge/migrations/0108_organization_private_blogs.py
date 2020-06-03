from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0107_submission_lock'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogpost',
            name='is_organization_private',
            field=models.BooleanField(default=False, verbose_name='private to organizations'),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='organizations',
            field=models.ManyToManyField(blank=True, help_text='If private, only these organizations may see the blog post.', to='judge.Organization', verbose_name='organizations'),
        ),
    ]
