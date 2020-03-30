# Generated by Django 2.2.6 on 2019-11-08 01:27

import django.db.models.deletion
from django.db import migrations, models

import judge.models.runtime


def create_python3(apps, schema_editor):
    Language = apps.get_model('judge', 'Language')
    Language.objects.get_or_create(key='PY3', defaults={'name': 'Python 3'})[0]


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0096_disqualified_submissions'),
    ]

    operations = [
        migrations.RunPython(create_python3, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='profile',
            name='language',
            field=models.ForeignKey(default=judge.models.runtime.Language.get_default_language_pk, on_delete=django.db.models.deletion.SET_DEFAULT, to='judge.Language', verbose_name='preferred language'),
        ),
    ]
