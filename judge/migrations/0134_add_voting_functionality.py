import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0133_add_problem_data_hints'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_banned_from_problem_voting',
            field=models.BooleanField(default=False,
                                      help_text="User will not be able to vote on problems' point values.",
                                      verbose_name='banned from voting on problem point values'),
        ),
        migrations.CreateModel(
            name='ProblemPointsVote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('points', models.IntegerField(help_text='The amount of points the voter thinks this problem deserves.',
                                               validators=[django.core.validators.MinValueValidator(1),
                                                           django.core.validators.MaxValueValidator(50)],
                                               verbose_name='proposed points')),
                ('note', models.TextField(blank=True, default='', help_text='Justification for problem point value.',
                                          max_length=8192, verbose_name='note')),
                ('problem', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name='problem_points_votes', to='judge.Problem',
                                              verbose_name='problem')),
                ('voter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                            related_name='problem_points_votes', to='judge.Profile',
                                            verbose_name='voter')),
                ('vote_time', models.DateTimeField(auto_now_add=True, help_text='The time this vote was cast.',
                                                   verbose_name='vote time')),
            ],
            options={
                'verbose_name': 'problem vote',
                'verbose_name_plural': 'problem votes',
            },
        ),
    ]
