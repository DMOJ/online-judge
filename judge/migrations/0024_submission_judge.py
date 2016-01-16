# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0023_contest_tag'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='judged_on',
            field=models.ForeignKey('Judge', verbose_name='Judged on', null=True, blank=True, on_delete=models.SET_NULL),
        ),
    ]
