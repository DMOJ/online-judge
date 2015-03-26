# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0003_license_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='LanguageLimit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time_limit', models.FloatField()),
                ('memory_limit', models.IntegerField()),
                ('language', models.ForeignKey(to='judge.Language')),
                ('problem', models.ForeignKey(to='judge.Problem')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='languagelimit',
            unique_together=set([('problem', 'language')]),
        ),
        migrations.AlterField(
            model_name='comment',
            name='body',
            field=models.TextField(verbose_name=b'Body of comment'),
            preserve_default=True,
        ),
    ]
