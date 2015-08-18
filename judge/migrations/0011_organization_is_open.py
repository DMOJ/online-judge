# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0010_comment_page_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='is_open',
            field=models.BooleanField(default=True, help_text=b'Allow joining organization'),
            preserve_default=True,
        ),
    ]
