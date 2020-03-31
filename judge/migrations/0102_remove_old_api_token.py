from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0101_submission_judged_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='api_token',
        ),
    ]
