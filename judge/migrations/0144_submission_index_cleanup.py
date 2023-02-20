import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('judge', '0143_contest_problem_rank_index'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='contest_object',
            field=models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='judge.contest', verbose_name='contest'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='language',
            field=models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE, to='judge.language',
                                    verbose_name='submission language'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='problem',
            field=models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE, to='judge.problem',
                                    verbose_name='problem'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='user',
            field=models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE, to='judge.profile',
                                    verbose_name='user'),
        ),
        migrations.AlterField(
            model_name='submissiontestcase',
            name='submission',
            field=models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='test_cases', to='judge.submission',
                                    verbose_name='associated submission'),
        ),
    ]
