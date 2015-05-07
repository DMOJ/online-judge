# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0008_contestproblem_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='solution',
            name='problem',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name=b'Associated problem', blank=True, to='judge.Problem', null=True),
            preserve_default=True,
        ),
    ]
