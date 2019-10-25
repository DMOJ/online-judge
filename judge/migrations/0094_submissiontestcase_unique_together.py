from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('judge', '0093_contest_moss'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='submissiontestcase',
            unique_together={('submission', 'case')},
        ),
    ]
