# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-10-06 21:42
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0071_auto_20180928_0103'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='first_submission_bonus',
            field=models.IntegerField(default=0, help_text='Bonus points for fully solving on first submission.', verbose_name='first submission bonus'),
        ),
    ]
