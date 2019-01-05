# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2019-01-05 22:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0079_remove_comment_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_unlisted',
            field=models.BooleanField(default=False, help_text='User will not be ranked.', verbose_name='unlisted user'),
        ),
    ]

