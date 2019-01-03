# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-11-21 00:23
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
from django.db.models import F

def compute_user_count(apps, schema_editor):
    Problem = apps.get_model('judge', 'Problem')
    for problem in Problem.objects.using(schema_editor.connection.alias):
        submissions = problem.submission_set.count()

        problem.user_count = problem.submission_set.filter(points__gte=problem.points, result='AC').values('user').distinct().count()
        problem.ac_rate = 100.0 * problem.submission_set.filter(points__gte=problem.points, result='AC').count() / submissions if submissions else 0
        problem.save()

def compute_old_user_count(apps, schema_editor):
    Problem = apps.get_model('judge', 'Problem')
    for problem in Problem.objects.using(schema_editor.connection.alias):
        submissions = problem.submission_set.count()

        problem.user_count = problem.submission_set.filter(points__gt=0).values('user').distinct().count()
        problem.ac_rate = 100.0 * problem.submission_set.filter(result='AC').count() / submissions if submissions else 0
        problem.save()

class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0075_organization_admin_reverse'),
    ]

    operations = [
        migrations.AlterField(
            model_name='problem',
            name='ac_rate',
            field=models.FloatField(default=0, verbose_name='solve rate'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='user_count',
            field=models.IntegerField(default=0, help_text='The number of users who solved the problem.', verbose_name='number of users'),
        ),
        migrations.RunPython(compute_user_count, compute_old_user_count),
    ]
