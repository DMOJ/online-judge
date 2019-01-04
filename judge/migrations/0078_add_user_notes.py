# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-12-05 23:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0077_remove_organization_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='notes',
            field=models.TextField(blank=True, help_text='Notes for administrators regarding this user.', null=True, verbose_name='internal notes'),
        ),
    ]
