# Generated by Django 2.2.28 on 2022-05-23 21:38

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import judge.models.contest
import judge.models.problem


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0132_no_self_vote'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='commentlock',
            options={'permissions': (('override_comment_lock', 'Override comment lock'),), 'verbose_name': 'comment lock', 'verbose_name_plural': 'comment locks'},
        ),
        migrations.AlterModelOptions(
            name='contest',
            options={'permissions': (('see_private_contest', 'See private contests'), ('join_all_contest', 'Join all contests'), ('edit_own_contest', 'Edit own contests'), ('edit_all_contest', 'Edit all contests'), ('clone_contest', 'Clone contest'), ('moss_contest', 'MOSS contest'), ('contest_rating', 'Rate contests'), ('contest_access_code', 'Contest access codes'), ('create_private_contest', 'Create private contests'), ('change_contest_visibility', 'Change contest visibility'), ('contest_problem_label', 'Edit contest problem label script'), ('lock_contest', 'Change lock status of contest')), 'verbose_name': 'contest', 'verbose_name_plural': 'contests'},
        ),
        migrations.AlterModelOptions(
            name='contestproblem',
            options={'ordering': ('order',), 'verbose_name': 'contest problem', 'verbose_name_plural': 'contest problems'},
        ),
        migrations.AlterModelOptions(
            name='problemclarification',
            options={'verbose_name': 'problem clarification', 'verbose_name_plural': 'problem clarifications'},
        ),
        migrations.AlterModelOptions(
            name='submissionsource',
            options={'verbose_name': 'submission source', 'verbose_name_plural': 'submission sources'},
        ),
        migrations.AlterModelOptions(
            name='ticket',
            options={'verbose_name': 'ticket', 'verbose_name_plural': 'tickets'},
        ),
        migrations.AlterModelOptions(
            name='ticketmessage',
            options={'verbose_name': 'ticket message', 'verbose_name_plural': 'ticket messages'},
        ),
        migrations.AlterModelOptions(
            name='webauthncredential',
            options={'verbose_name': 'WebAuthn credential', 'verbose_name_plural': 'WebAuthn credentials'},
        ),
        migrations.RemoveField(
            model_name='contest',
            name='is_locked',
        ),
        migrations.RemoveField(
            model_name='submission',
            name='is_locked',
        ),
        migrations.AddField(
            model_name='contest',
            name='locked_after',
            field=models.DateTimeField(blank=True, help_text='Prevent submissions from this contest from being rejudged after this date.', null=True, verbose_name='contest lock'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='authors',
            field=models.ManyToManyField(help_text='These users will be able to edit the contest.', related_name='authored_contests', to='judge.Profile', verbose_name='authors'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='curators',
            field=models.ManyToManyField(blank=True, help_text='These users will be able to edit the contest, but will not be listed as authors.', related_name='curated_contests', to='judge.Profile', verbose_name='curators'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='format_name',
            field=models.CharField(choices=[('atcoder', 'AtCoder'), ('bonuses', 'Bonuses'), ('default', 'Default'), ('ecoo', 'ECOO'), ('icpc', 'ICPC'), ('ics3u', 'ICS3U'), ('ioi', 'IOI (pre-2016)'), ('ioi16', 'IOI')], default='default', help_text='The contest format module to use.', max_length=32, verbose_name='contest format'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='organizations',
            field=models.ManyToManyField(blank=True, help_text='If non-empty, only these organizations may join the contest', to='judge.Organization', verbose_name='organizations'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='private_contestants',
            field=models.ManyToManyField(blank=True, help_text='If non-empty, only these users may see the contest', related_name='_contest_private_contestants_+', to='judge.Profile', verbose_name='private contestants'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='scoreboard_visibility',
            field=models.CharField(choices=[('H', 'Hidden'), ('V', 'Visible'), ('C', 'Hidden for duration of contest'), ('P', 'Hidden for duration of participation'), ('H', 'Hidden permanently')], default='V', help_text='Scoreboard visibility through the duration of the contest', max_length=1, verbose_name='scoreboard visibility'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='spectators',
            field=models.ManyToManyField(blank=True, help_text='These users will be able to spectate the contest, but not see the problems ahead of time.', related_name='spectated_contests', to='judge.Profile', verbose_name='spectators'),
        ),
        migrations.AlterField(
            model_name='contest',
            name='testers',
            field=models.ManyToManyField(blank=True, help_text='These users will be able to view the contest, but not edit it.', related_name='tested_contests', to='judge.Profile', verbose_name='testers'),
        ),
        migrations.AlterField(
            model_name='contestproblem',
            name='max_submissions',
            field=models.IntegerField(blank=True, default=None, help_text='Maximum number of submissions for this problem, or leave blank for no limit.', null=True, validators=[judge.models.contest.MinValueOrNoneValidator(1, "Why include a problem you can't submit to?")], verbose_name='max submissions'),
        ),
        migrations.AlterField(
            model_name='judge',
            name='auth_key',
            field=models.CharField(help_text='A key to authenticate this judge', max_length=100, verbose_name='authentication key'),
        ),
        migrations.AlterField(
            model_name='judge',
            name='last_ip',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='last connected IP'),
        ),
        migrations.AlterField(
            model_name='judge',
            name='name',
            field=models.CharField(help_text='Server name, hostname-style', max_length=50, unique=True, verbose_name='judge name'),
        ),
        migrations.AlterField(
            model_name='language',
            name='description',
            field=models.TextField(blank=True, help_text='Use this field to inform users of quirks with your environment, additional restrictions, etc.', verbose_name='language description'),
        ),
        migrations.AlterField(
            model_name='languagelimit',
            name='memory_limit',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(1048576)], verbose_name='memory limit'),
        ),
        migrations.AlterField(
            model_name='languagelimit',
            name='time_limit',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(60)], verbose_name='time limit'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='allowed_languages',
            field=models.ManyToManyField(help_text='List of allowed submission languages.', to='judge.Language', verbose_name='allowed languages'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='authors',
            field=models.ManyToManyField(blank=True, help_text='These users will be able to edit the problem, and be listed as authors.', related_name='authored_problems', to='judge.Profile', verbose_name='creators'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='code',
            field=models.CharField(help_text='A short, unique code for the problem, used in the url after /problem/', max_length=20, unique=True, validators=[django.core.validators.RegexValidator('^[a-z0-9]+$', 'Problem code must be ^[a-z0-9]+$')], verbose_name='problem code'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='curators',
            field=models.ManyToManyField(blank=True, help_text='These users will be able to edit the problem, but not be listed as authors.', related_name='curated_problems', to='judge.Profile', verbose_name='curators'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='description',
            field=models.TextField(validators=[judge.models.problem.disallowed_characters_validator], verbose_name='problem body'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='group',
            field=models.ForeignKey(help_text='The group of problem, shown under Category in the problem list.', on_delete=django.db.models.deletion.CASCADE, to='judge.ProblemGroup', verbose_name='problem group'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='is_manually_managed',
            field=models.BooleanField(db_index=True, default=False, help_text='Whether judges should be allowed to manage data or not.', verbose_name='manually managed'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='license',
            field=models.ForeignKey(blank=True, help_text='The license under which this problem is published.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='judge.License', verbose_name='license'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='memory_limit',
            field=models.PositiveIntegerField(help_text='The memory limit for this problem, in kilobytes (e.g. 64mb = 65536 kilobytes).', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(1048576)], verbose_name='memory limit'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='name',
            field=models.CharField(db_index=True, help_text='The full name of the problem, as shown in the problem list.', max_length=100, verbose_name='problem name'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='points',
            field=models.FloatField(help_text="Points awarded for problem completion. Points are displayed with a 'p' suffix if partial.", validators=[django.core.validators.MinValueValidator(0)], verbose_name='points'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='short_circuit',
            field=models.BooleanField(default=False, verbose_name='short circuit'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='testers',
            field=models.ManyToManyField(blank=True, help_text='These users will be able to view the private problem, but not edit it.', related_name='tested_problems', to='judge.Profile', verbose_name='testers'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='time_limit',
            field=models.FloatField(help_text='The time limit for this problem, in seconds. Fractional seconds (e.g. 1.5) are supported.', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(60)], verbose_name='time limit'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='types',
            field=models.ManyToManyField(help_text="The type of problem, as shown on the problem's page.", to='judge.ProblemType', verbose_name='problem types'),
        ),
        migrations.AlterField(
            model_name='problemclarification',
            name='description',
            field=models.TextField(validators=[judge.models.problem.disallowed_characters_validator], verbose_name='clarification body'),
        ),
        migrations.AlterField(
            model_name='problemtranslation',
            name='description',
            field=models.TextField(validators=[judge.models.problem.disallowed_characters_validator], verbose_name='translated description'),
        ),
        migrations.AlterField(
            model_name='problemtranslation',
            name='language',
            field=models.CharField(choices=[('ca', 'Catalan'), ('de', 'German'), ('en', 'English'), ('es', 'Spanish'), ('fr', 'French'), ('hr', 'Croatian'), ('hu', 'Hungarian'), ('ja', 'Japanese'), ('ko', 'Korean'), ('pt', 'Brazilian Portuguese'), ('ro', 'Romanian'), ('ru', 'Russian'), ('sr-latn', 'Serbian (Latin)'), ('tr', 'Turkish'), ('vi', 'Vietnamese'), ('zh-hans', 'Simplified Chinese'), ('zh-hant', 'Traditional Chinese')], max_length=7, verbose_name='language'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='ace_theme',
            field=models.CharField(choices=[('ambiance', 'Ambiance'), ('chaos', 'Chaos'), ('chrome', 'Chrome'), ('clouds', 'Clouds'), ('clouds_midnight', 'Clouds Midnight'), ('cobalt', 'Cobalt'), ('crimson_editor', 'Crimson Editor'), ('dawn', 'Dawn'), ('dreamweaver', 'Dreamweaver'), ('eclipse', 'Eclipse'), ('github', 'Github'), ('idle_fingers', 'Idle Fingers'), ('katzenmilch', 'Katzenmilch'), ('kr_theme', 'KR Theme'), ('kuroir', 'Kuroir'), ('merbivore', 'Merbivore'), ('merbivore_soft', 'Merbivore Soft'), ('mono_industrial', 'Mono Industrial'), ('monokai', 'Monokai'), ('pastel_on_dark', 'Pastel on Dark'), ('solarized_dark', 'Solarized Dark'), ('solarized_light', 'Solarized Light'), ('terminal', 'Terminal'), ('textmate', 'Textmate'), ('tomorrow', 'Tomorrow'), ('tomorrow_night', 'Tomorrow Night'), ('tomorrow_night_blue', 'Tomorrow Night Blue'), ('tomorrow_night_bright', 'Tomorrow Night Bright'), ('tomorrow_night_eighties', 'Tomorrow Night Eighties'), ('twilight', 'Twilight'), ('vibrant_ink', 'Vibrant Ink'), ('xcode', 'XCode')], default='github', max_length=30, verbose_name='Ace theme'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='display_rank',
            field=models.CharField(choices=[('user', 'Normal User'), ('president', 'President'), ('alumnus', 'Alumnus'), ('admin', 'Admin')], default='user', max_length=10, verbose_name='display rank'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='is_totp_enabled',
            field=models.BooleanField(default=False, help_text='check to enable TOTP-based two-factor authentication', verbose_name='TOTP 2FA enabled'),
        ),
        migrations.AlterField(
            model_name='solution',
            name='content',
            field=models.TextField(validators=[judge.models.problem.disallowed_characters_validator], verbose_name='editorial content'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='problem',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='judge.Problem', verbose_name='problem'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='judge.Profile', verbose_name='user'),
        ),
    ]
