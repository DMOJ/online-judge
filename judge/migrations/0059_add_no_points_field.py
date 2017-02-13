# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-13 20:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0058_problem_curator_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='unlisted_user',
            field=models.BooleanField(verbose_name='unlisted user', help_text='User will not be ranked.', default=False)
        ),
    ]
