from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0147_judge_add_tiers'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contest',
            name='rate_all',
            field=models.BooleanField(default=False, help_text='Rate users even if they make no submissions.', verbose_name='rate all'),
        ),
    ]
