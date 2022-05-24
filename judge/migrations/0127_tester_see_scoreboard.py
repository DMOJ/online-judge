# Generated by Django 2.2.27 on 2022-02-26 04:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0126_infer_private_bools'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='tester_see_scoreboard',
            field=models.BooleanField(default=False, help_text='If testers can see the scoreboard.', verbose_name='testers see scoreboard'),
        ),
    ]
