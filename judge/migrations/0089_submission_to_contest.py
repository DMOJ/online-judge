# Generated by Django 2.1.12 on 2019-09-25 23:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0088_private_contests'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='contest_object',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='judge.Contest', verbose_name='contest'),
        ),
        migrations.RunSQL('''
            UPDATE `judge_submission`
                INNER JOIN `judge_contestsubmission`
                    ON (`judge_submission`.`id` = `judge_contestsubmission`.`submission_id`)
                INNER JOIN `judge_contestparticipation`
                    ON (`judge_contestsubmission`.`participation_id` = `judge_contestparticipation`.`id`)
            SET `judge_submission`.`contest_id` = `judge_contestparticipation`.`contest_id`
        ''', migrations.RunSQL.noop),
    ]
