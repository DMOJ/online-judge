# Generated by Django 2.2.28 on 2022-05-24 03:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0133_auto_20220523_2138'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='locked_after',
            field=models.DateTimeField(blank=True, null=True, verbose_name='submission lock'),
        ),
    ]
