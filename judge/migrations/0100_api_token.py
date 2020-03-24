# Generated by Django 2.2.10 on 2020-03-18 23:10

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0099_contest_problem_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='api_token',
            field=models.CharField(help_text='32 character base32-encoded API access token', max_length=32, null=True, validators=[django.core.validators.RegexValidator('^$|^[a-z2-7]{32}$', 'API token must be empty or base32')], verbose_name='API token'),
        ),
    ]
