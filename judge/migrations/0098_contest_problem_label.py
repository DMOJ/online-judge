# Generated by Django 2.2.11 on 2020-03-24 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0097_participation_is_disqualified'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='problem_label_script',
            field=models.TextField(blank=True, help_text='A custom Lua function to generate problem labels. Requires a single function with an integer parameter, the zero-indexed contest problem index, and returns a string, the label.', verbose_name='contest problem label script'),
        ),
        migrations.AlterModelOptions(
            name='contest',
            options={'permissions': (('see_private_contest', 'See private contests'), ('edit_own_contest', 'Edit own contests'), ('edit_all_contest', 'Edit all contests'), ('clone_contest', 'Clone contest'), ('moss_contest', 'MOSS contest'), ('contest_rating', 'Rate contests'), ('contest_access_code', 'Contest access codes'), ('create_private_contest', 'Create private contests'), ('contest_problem_label', 'Edit contest problem label script')), 'verbose_name': 'contest', 'verbose_name_plural': 'contests'},
        ),
    ]
