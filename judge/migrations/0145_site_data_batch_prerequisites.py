# Generated by Django 3.2.21 on 2024-01-06 04:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0144_submission_index_cleanup'),
    ]

    operations = [
        migrations.AddField(
            model_name='problemtestcase',
            name='batch_dependencies',
            field=models.TextField(blank=True, help_text='batch dependencies as a comma-separated list of integers', verbose_name='batch dependencies'),
        ),
    ]
