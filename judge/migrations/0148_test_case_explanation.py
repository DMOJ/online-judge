# Generated by Django 3.2.25 on 2024-08-18 07:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0147_infer_test_cases_from_zip'),
    ]

    operations = [
        migrations.AddField(
            model_name='problemtestcase',
            name='explanation_file',
            field=models.CharField(blank=True, null=True, default='', max_length=100, verbose_name='explanation file name'),
        ),
    ]
