# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0012_organization_perms'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='is_private',
            field=models.BooleanField(default=False, verbose_name=b'Private to organizations'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contest',
            name='organizations',
            field=models.ManyToManyField(help_text=b'If private, only these organizations may see the contest', to='judge.Organization', blank=True),
            preserve_default=True,
        ),
    ]
