# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from django.db import models, migrations


def add_contest_problem_order(apps, schema_editor):
    ContestProblem = apps.get_model('judge', 'ContestProblem')
    db_alias = schema_editor.connection.alias
    order = defaultdict(int)
    for cp in ContestProblem.objects.using(db_alias):
        cp.order = order[cp.contest_id]
        cp.save()
        order[cp.contest_id] += 1


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0007_test_site_perm'),
    ]

    operations = [
        migrations.AddField(
            model_name='contestproblem',
            name='order',
            field=models.PositiveIntegerField(default=0, db_index=True),
            preserve_default=False,
        ),
        migrations.RunPython(add_contest_problem_order, migrations.RunPython.noop),
    ]

