from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0152_deactivate_user_permission'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='ratable_users',
            field=models.ManyToManyField(blank=True, help_text='Users who are eligible to be rated in this contest.', related_name='ratable_contests+', to='judge.profile', verbose_name='ratable users'),
        ),
    ]
