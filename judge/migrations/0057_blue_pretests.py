# -*- coding: utf-8 -*-
# Generated by Kirito Feng on shrooms
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0056_ticket_is_open'),
    ]

    operations = [
        migrations.AddField(
            model_name='contestproblem',
            name='is_pretested',
            field=models.BooleanField(default=False, verbose_name='is pretested'),
        ),
]
