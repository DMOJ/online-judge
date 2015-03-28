# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='License',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=20)),
                ('link', models.CharField(max_length=256)),
                ('name', models.CharField(max_length=256)),
                ('display', models.CharField(help_text=b'Displayed on pages under this license', max_length=256, blank=True)),
                ('icon', models.CharField(help_text=b'URL to the icon', max_length=256, blank=True)),
                ('text', models.TextField(verbose_name=b'License text')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='problem',
            name='license',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='judge.License', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='blogpost',
            name='sticky',
            field=models.BooleanField(default=False, verbose_name=b'Sticky'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='blogpost',
            name='visible',
            field=models.BooleanField(default=False, verbose_name=b'Public visibility'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='contestproblem',
            name='partial',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='privatemessage',
            name='read',
            field=models.BooleanField(default=False, verbose_name=b'Read'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='problem',
            name='is_public',
            field=models.BooleanField(default=False, db_index=True, verbose_name=b'Publicly visible'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='problem',
            name='partial',
            field=models.BooleanField(default=False, verbose_name=b'Allows partial points'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='solution',
            name='is_public',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
