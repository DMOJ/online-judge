# Generated by Django 2.2.24 on 2021-06-06 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0118_convert_to_dates'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='hide_problem_authors',
            field=models.BooleanField(
                default=False,
                help_text='Whether problem authors should be hidden by default.',
                verbose_name='hide problem authors',
            ),
        ),
    ]
