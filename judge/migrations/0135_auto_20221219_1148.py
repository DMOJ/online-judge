# Generated by Django 3.2.16 on 2022-12-19 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0134_problemdata_hints'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='problemdata',
            name='binary_data',
        ),
        migrations.RemoveField(
            model_name='problemdata',
            name='hints',
        ),
        migrations.AddField(
            model_name='problemdata',
            name='nobigmath',
            field=models.BooleanField(blank=True, null=True, verbose_name='disable biginteger/bigdecimal'),
        ),
        migrations.AddField(
            model_name='problemdata',
            name='unicode',
            field=models.BooleanField(blank=True, null=True, verbose_name='enable unicode'),
        ),
    ]
