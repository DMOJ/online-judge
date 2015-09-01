# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0015_remove_single_organization'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganizationRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time', models.DateTimeField(verbose_name=b'Request time', auto_now_add=True)),
                ('state', models.CharField(max_length=1, choices=[(b'P', b'Pending'), (b'A', b'Approved'), (b'R', b'Rejected')])),
                ('reason', models.TextField()),
                ('organization', models.ForeignKey(to='judge.Organization', related_name='requests')),
                ('user', models.ForeignKey(to='judge.Profile', related_name='requests')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
