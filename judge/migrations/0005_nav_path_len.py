# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0004_language_limit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='navigationbar',
            name='path',
            field=models.CharField(max_length=255, verbose_name=b'Link path'),
            preserve_default=True,
        ),
    ]
