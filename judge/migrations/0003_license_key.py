# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0002_license'),
    ]

    operations = [
        migrations.AlterField(
            model_name='license',
            name='key',
            field=models.CharField(unique=True, max_length=20, validators=[django.core.validators.RegexValidator(b'^[-\\w.]+$', b'License key must be ^[-\\w.]+$')]),
            preserve_default=True,
        ),
    ]
