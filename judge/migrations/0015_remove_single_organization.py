# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def to_foreign_key_organization(apps, schema_editor):
    Profile = apps.get_model('judge', 'profile')
    for link in Profile.organizations.through.objects.all():
        Profile.objects.filter(id=link.profile_id).update(organization_id=link.organization_id)


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0014_multi_organization'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='organization_join_time',
        ),
        migrations.RunPython(lambda apps, schema_editor: None, to_foreign_key_organization),
        migrations.RemoveField(
            model_name='profile',
            name='organization',
        ),
    ]
