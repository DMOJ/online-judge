# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0016_organizationrequest'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='problem',
            options={'permissions': (('see_private_problem', 'See hidden problems'), ('edit_own_problem', 'Edit own problems'), ('edit_all_problem', 'Edit all problems'), ('edit_public_problem', 'Edit all public problems'), ('clone_problem', 'Clone problem'))},
        ),
    ]
