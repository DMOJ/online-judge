# Generated by Django 2.2.12 on 2020-05-13 20:58

from django.db import migrations, models
from django.utils import timezone


def updatecontestsubmissions(apps, schema_editor):
    Contest = apps.get_model('judge', 'Contest')
    Contest.objects.filter(end_time__lt=timezone.now()).update(is_locked=True)

    Submission = apps.get_model('judge', 'Submission')
    Submission.objects.filter(contest_object__is_locked=True, contest__participation__virtual=0).update(is_locked=True)


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0106_user_data_download'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='contest',
            options={
                'permissions': (
                    ('see_private_contest', 'See private contests'),
                    ('edit_own_contest', 'Edit own contests'),
                    ('edit_all_contest', 'Edit all contests'),
                    ('clone_contest', 'Clone contest'),
                    ('moss_contest', 'MOSS contest'),
                    ('contest_rating', 'Rate contests'),
                    ('contest_access_code', 'Contest access codes'),
                    ('create_private_contest', 'Create private contests'),
                    ('change_contest_visibility', 'Change contest visibility'),
                    ('contest_problem_label', 'Edit contest problem label script'),
                    ('lock_contest', 'Change lock status of contest'),
                ),
                'verbose_name': 'contest',
                'verbose_name_plural': 'contests',
            },
        ),
        migrations.AlterModelOptions(
            name='submission',
            options={
                'permissions': (
                    ('abort_any_submission', 'Abort any submission'),
                    ('rejudge_submission', 'Rejudge the submission'),
                    ('rejudge_submission_lot', 'Rejudge a lot of submissions'),
                    ('spam_submission', 'Submit without limit'),
                    ('view_all_submission', 'View all submission'),
                    ('resubmit_other', "Resubmit others' submission"),
                    ('lock_submission', 'Change lock status of submission'),
                ),
                'verbose_name': 'submission',
                'verbose_name_plural': 'submissions',
            },
        ),
        migrations.AddField(
            model_name='contest',
            name='is_locked',
            field=models.BooleanField(
                default=False,
                help_text='Prevent submissions from this contest from being rejudged.',
                verbose_name='contest lock',
            ),
        ),
        migrations.AddField(
            model_name='submission',
            name='is_locked',
            field=models.BooleanField(default=False, verbose_name='lock submission'),
        ),
        migrations.RunPython(updatecontestsubmissions, reverse_code=migrations.RunPython.noop),
    ]
