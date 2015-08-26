# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def to_many_to_many_organization(apps, schema_editor):
    Profile = apps.get_model('judge', 'profile')
    ProfileToOrganization = Profile.organizations.through
    ProfileToOrganization.objects.bulk_create([
        ProfileToOrganization(profile_id=p.id, organization_id=p.organization_id)
        for p in Profile.objects.filter(organization__isnull=False)
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0013_private_contests'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='organizations',
            field=models.ManyToManyField(related_query_name=b'member', related_name='members', verbose_name=b'Organization', to='judge.Organization', blank=True),
            preserve_default=True,
        ),
        migrations.RunPython(to_many_to_many_organization, lambda apps, schema_editor: None),
    ]
