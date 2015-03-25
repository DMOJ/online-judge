# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import mptt.fields
import django.utils.timezone
import judge.models
import django.db.models.deletion
from django.conf import settings
import timedelta.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BlogPost',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100, verbose_name=b'Post title')),
                ('slug', models.SlugField(verbose_name=b'Slug')),
                ('visible', models.BooleanField(verbose_name=b'Public visibility')),
                ('sticky', models.BooleanField(verbose_name=b'Sticky')),
                ('publish_on', models.DateTimeField(verbose_name=b'Publish after')),
                ('content', models.TextField(verbose_name=b'Post content')),
                ('summary', models.TextField(verbose_name=b'Post summary', blank=True)),
            ],
            options={
                'permissions': (('see_hidden_post', 'See hidden posts'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time', models.DateTimeField(auto_now_add=True, verbose_name=b'Posted time')),
                ('page', models.CharField(max_length=30, verbose_name=b'Associated Page', validators=[django.core.validators.RegexValidator(b'^[pc]:[a-z0-9]+$|^b:\\d+$|^s:', b'Page code must be ^[pc]:[a-z0-9]+$|^b:\\d+$')])),
                ('score', models.IntegerField(default=0, verbose_name=b'Votes')),
                ('title', models.CharField(max_length=200, verbose_name=b'Title of comment')),
                ('body', models.TextField(verbose_name=b'Body of comment', blank=True)),
                ('hidden', models.BooleanField(default=0, verbose_name=b'Hide the comment')),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CommentVote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('score', models.IntegerField()),
                ('comment', models.ForeignKey(to='judge.Comment')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Contest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(unique=True, max_length=20, verbose_name=b'Contest id', validators=[django.core.validators.RegexValidator(b'^[a-z0-9]+$', b'Contest id must be ^[a-z0-9]+$')])),
                ('name', models.CharField(max_length=100, verbose_name=b'Contest name', db_index=True)),
                ('description', models.TextField(blank=True)),
                ('start_time', models.DateTimeField(db_index=True)),
                ('end_time', models.DateTimeField(db_index=True)),
                (b'time_limit', timedelta.fields.TimedeltaField(max_value=None, min_value=None)),
                ('is_public', models.BooleanField(default=False, verbose_name=b'Publicly visible')),
                ('is_external', models.BooleanField(default=False, verbose_name=b'External contest')),
                ('is_rated', models.BooleanField(default=False, help_text=b'Whether this contest can be rated.')),
                ('rate_all', models.BooleanField(default=False, help_text=b'Rate all users who joined.')),
            ],
            options={
                'permissions': (('see_private_contest', 'See private contests'), ('edit_own_contest', 'Edit own contests'), ('edit_all_contest', 'Edit all contests'), ('contest_rating', 'Rate contests')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContestParticipation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('real_start', models.DateTimeField(default=django.utils.timezone.now, verbose_name=b'Start time', db_column=b'start')),
                ('score', models.IntegerField(default=0, verbose_name=b'score', db_index=True)),
                ('cumtime', models.PositiveIntegerField(default=0, verbose_name=b'Cumulative time')),
                ('contest', models.ForeignKey(related_name='users', verbose_name=b'Associated contest', to='judge.Contest')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContestProblem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('points', models.IntegerField()),
                ('partial', models.BooleanField()),
                ('contest', models.ForeignKey(related_name='contest_problems', to='judge.Contest')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContestProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('current', models.OneToOneField(related_name='+', null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='judge.ContestParticipation', verbose_name=b'Current contest')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContestSubmission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('points', models.FloatField(default=0.0)),
                ('participation', models.ForeignKey(related_query_name=b'submission', related_name='submissions', to='judge.ContestParticipation')),
                ('problem', models.ForeignKey(related_query_name=b'submission', related_name='submissions', to='judge.ContestProblem')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Judge',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Server name, hostname-style', unique=True, max_length=50)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('auth_key', models.CharField(help_text=b'A key to authenticated this judge', max_length=100, verbose_name=b'Authentication key')),
                ('online', models.BooleanField(default=False)),
                ('last_connect', models.DateTimeField(null=True, verbose_name=b'Last connection time')),
                ('ping', models.FloatField(null=True, verbose_name=b'Response time')),
                ('load', models.FloatField(help_text=b'Load for the last minute, divided by processors to be fair.', null=True, verbose_name=b'System load')),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-online', 'load'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(unique=True, max_length=6, verbose_name=b'Short identifier')),
                ('name', models.CharField(max_length=20, verbose_name=b'Long name')),
                ('short_name', models.CharField(max_length=10, null=True, verbose_name=b'Short name', blank=True)),
                ('common_name', models.CharField(max_length=10, verbose_name=b'Common name')),
                ('ace', models.CharField(max_length=20, verbose_name=b'ACE mode name')),
                ('pygments', models.CharField(max_length=20, verbose_name=b'Pygments Name')),
                ('info', models.CharField(max_length=50, verbose_name=b'Basic runtime info', blank=True)),
                ('description', models.TextField(verbose_name=b'Description for model', blank=True)),
            ],
            options={
                'ordering': ['key'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MiscConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=30, db_index=True)),
                ('value', models.TextField(blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NavigationBar',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveIntegerField(db_index=True)),
                ('key', models.CharField(unique=True, max_length=10, verbose_name=b'Identifier')),
                ('label', models.CharField(max_length=20)),
                ('path', models.CharField(max_length=30, verbose_name=b'Link path')),
                ('regex', models.TextField(verbose_name=b'Highlight regex', validators=[judge.models.validate_regex])),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
                ('parent', mptt.fields.TreeForeignKey(related_name='children', verbose_name=b'Parent item', blank=True, to='judge.NavigationBar', null=True)),
            ],
            options={
                'verbose_name': 'navigation item',
                'verbose_name_plural': 'navigation bar',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, verbose_name=b'Organization title')),
                ('key', models.CharField(help_text=b'Organization name shows in URL', unique=True, max_length=6, verbose_name=b'Identifier', validators=[django.core.validators.RegexValidator(b'^[A-Za-z0-9]+$', b'Identifier must contain letters and numbers only')])),
                ('short_name', models.CharField(help_text=b'Displayed beside user name during contests', max_length=20, verbose_name=b'Short name')),
                ('about', models.TextField(verbose_name=b'Organization description')),
                ('creation_date', models.DateTimeField(auto_now_add=True, verbose_name=b'Creation date')),
            ],
            options={
                'ordering': ['key'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PrivateMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=50, verbose_name=b'Message title')),
                ('content', models.TextField(verbose_name=b'Message body')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name=b'Message timestamp')),
                ('read', models.BooleanField(verbose_name=b'Read')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PrivateMessageThread',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('messages', models.ManyToManyField(to='judge.PrivateMessage', verbose_name=b'Messages in the thread')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Problem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(unique=True, max_length=20, verbose_name=b'Problem code', validators=[django.core.validators.RegexValidator(b'^[a-z0-9]+$', b'Problem code must be ^[a-z0-9]+$')])),
                ('name', models.CharField(max_length=100, verbose_name=b'Problem name', db_index=True)),
                ('description', models.TextField(verbose_name=b'Problem body')),
                ('time_limit', models.FloatField(verbose_name=b'Time limit')),
                ('memory_limit', models.IntegerField(verbose_name=b'Memory limit')),
                ('short_circuit', models.BooleanField(default=False)),
                ('points', models.FloatField(verbose_name=b'Points')),
                ('partial', models.BooleanField(verbose_name=b'Allows partial points')),
                ('is_public', models.BooleanField(db_index=True, verbose_name=b'Publicly visible')),
                ('date', models.DateTimeField(help_text=b"Doesn't have magic ability to auto-publish due to backward compatibility", null=True, verbose_name=b'Date of publishing', db_index=True, blank=True)),
                ('allowed_languages', models.ManyToManyField(to='judge.Language', verbose_name=b'Allowed languages')),
            ],
            options={
                'permissions': (('see_private_problem', 'See hidden problems'), ('edit_own_problem', 'Edit own problems'), ('edit_all_problem', 'Edit all problems'), ('clone_problem', 'Clone problem')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProblemGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=20, verbose_name=b'Problem group ID')),
                ('full_name', models.CharField(max_length=100, verbose_name=b'Problem group name')),
            ],
            options={
                'ordering': ['full_name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProblemType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=20, verbose_name=b'Problem category ID')),
                ('full_name', models.CharField(max_length=100, verbose_name=b'Problem category name')),
            ],
            options={
                'ordering': ['full_name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, null=True, verbose_name=b'Display name', blank=True)),
                ('about', models.TextField(null=True, verbose_name=b'Self-description', blank=True)),
                ('timezone', models.CharField(default=b'America/Toronto', max_length=50, verbose_name=b'Location', choices=[(b'Africa', [(b'Africa/Abidjan', b'Abidjan'), (b'Africa/Accra', b'Accra'), (b'Africa/Addis_Ababa', b'Addis_Ababa'), (b'Africa/Algiers', b'Algiers'), (b'Africa/Asmara', b'Asmara'), (b'Africa/Asmera', b'Asmera'), (b'Africa/Bamako', b'Bamako'), (b'Africa/Bangui', b'Bangui'), (b'Africa/Banjul', b'Banjul'), (b'Africa/Bissau', b'Bissau'), (b'Africa/Blantyre', b'Blantyre'), (b'Africa/Brazzaville', b'Brazzaville'), (b'Africa/Bujumbura', b'Bujumbura'), (b'Africa/Cairo', b'Cairo'), (b'Africa/Casablanca', b'Casablanca'), (b'Africa/Ceuta', b'Ceuta'), (b'Africa/Conakry', b'Conakry'), (b'Africa/Dakar', b'Dakar'), (b'Africa/Dar_es_Salaam', b'Dar_es_Salaam'), (b'Africa/Djibouti', b'Djibouti'), (b'Africa/Douala', b'Douala'), (b'Africa/El_Aaiun', b'El_Aaiun'), (b'Africa/Freetown', b'Freetown'), (b'Africa/Gaborone', b'Gaborone'), (b'Africa/Harare', b'Harare'), (b'Africa/Johannesburg', b'Johannesburg'), (b'Africa/Juba', b'Juba'), (b'Africa/Kampala', b'Kampala'), (b'Africa/Khartoum', b'Khartoum'), (b'Africa/Kigali', b'Kigali'), (b'Africa/Kinshasa', b'Kinshasa'), (b'Africa/Lagos', b'Lagos'), (b'Africa/Libreville', b'Libreville'), (b'Africa/Lome', b'Lome'), (b'Africa/Luanda', b'Luanda'), (b'Africa/Lubumbashi', b'Lubumbashi'), (b'Africa/Lusaka', b'Lusaka'), (b'Africa/Malabo', b'Malabo'), (b'Africa/Maputo', b'Maputo'), (b'Africa/Maseru', b'Maseru'), (b'Africa/Mbabane', b'Mbabane'), (b'Africa/Mogadishu', b'Mogadishu'), (b'Africa/Monrovia', b'Monrovia'), (b'Africa/Nairobi', b'Nairobi'), (b'Africa/Ndjamena', b'Ndjamena'), (b'Africa/Niamey', b'Niamey'), (b'Africa/Nouakchott', b'Nouakchott'), (b'Africa/Ouagadougou', b'Ouagadougou'), (b'Africa/Porto-Novo', b'Porto-Novo'), (b'Africa/Sao_Tome', b'Sao_Tome'), (b'Africa/Timbuktu', b'Timbuktu'), (b'Africa/Tripoli', b'Tripoli'), (b'Africa/Tunis', b'Tunis'), (b'Africa/Windhoek', b'Windhoek')]), (b'America', [(b'America/Adak', b'Adak'), (b'America/Anchorage', b'Anchorage'), (b'America/Anguilla', b'Anguilla'), (b'America/Antigua', b'Antigua'), (b'America/Araguaina', b'Araguaina'), (b'America/Argentina/Buenos_Aires', b'Argentina/Buenos_Aires'), (b'America/Argentina/Catamarca', b'Argentina/Catamarca'), (b'America/Argentina/ComodRivadavia', b'Argentina/ComodRivadavia'), (b'America/Argentina/Cordoba', b'Argentina/Cordoba'), (b'America/Argentina/Jujuy', b'Argentina/Jujuy'), (b'America/Argentina/La_Rioja', b'Argentina/La_Rioja'), (b'America/Argentina/Mendoza', b'Argentina/Mendoza'), (b'America/Argentina/Rio_Gallegos', b'Argentina/Rio_Gallegos'), (b'America/Argentina/Salta', b'Argentina/Salta'), (b'America/Argentina/San_Juan', b'Argentina/San_Juan'), (b'America/Argentina/San_Luis', b'Argentina/San_Luis'), (b'America/Argentina/Tucuman', b'Argentina/Tucuman'), (b'America/Argentina/Ushuaia', b'Argentina/Ushuaia'), (b'America/Aruba', b'Aruba'), (b'America/Asuncion', b'Asuncion'), (b'America/Atikokan', b'Atikokan'), (b'America/Atka', b'Atka'), (b'America/Bahia', b'Bahia'), (b'America/Bahia_Banderas', b'Bahia_Banderas'), (b'America/Barbados', b'Barbados'), (b'America/Belem', b'Belem'), (b'America/Belize', b'Belize'), (b'America/Blanc-Sablon', b'Blanc-Sablon'), (b'America/Boa_Vista', b'Boa_Vista'), (b'America/Bogota', b'Bogota'), (b'America/Boise', b'Boise'), (b'America/Buenos_Aires', b'Buenos_Aires'), (b'America/Cambridge_Bay', b'Cambridge_Bay'), (b'America/Campo_Grande', b'Campo_Grande'), (b'America/Cancun', b'Cancun'), (b'America/Caracas', b'Caracas'), (b'America/Catamarca', b'Catamarca'), (b'America/Cayenne', b'Cayenne'), (b'America/Cayman', b'Cayman'), (b'America/Chicago', b'Chicago'), (b'America/Chihuahua', b'Chihuahua'), (b'America/Coral_Harbour', b'Coral_Harbour'), (b'America/Cordoba', b'Cordoba'), (b'America/Costa_Rica', b'Costa_Rica'), (b'America/Creston', b'Creston'), (b'America/Cuiaba', b'Cuiaba'), (b'America/Curacao', b'Curacao'), (b'America/Danmarkshavn', b'Danmarkshavn'), (b'America/Dawson', b'Dawson'), (b'America/Dawson_Creek', b'Dawson_Creek'), (b'America/Denver', b'Denver'), (b'America/Detroit', b'Detroit'), (b'America/Dominica', b'Dominica'), (b'America/Edmonton', b'Edmonton'), (b'America/Eirunepe', b'Eirunepe'), (b'America/El_Salvador', b'El_Salvador'), (b'America/Ensenada', b'Ensenada'), (b'America/Fort_Wayne', b'Fort_Wayne'), (b'America/Fortaleza', b'Fortaleza'), (b'America/Glace_Bay', b'Glace_Bay'), (b'America/Godthab', b'Godthab'), (b'America/Goose_Bay', b'Goose_Bay'), (b'America/Grand_Turk', b'Grand_Turk'), (b'America/Grenada', b'Grenada'), (b'America/Guadeloupe', b'Guadeloupe'), (b'America/Guatemala', b'Guatemala'), (b'America/Guayaquil', b'Guayaquil'), (b'America/Guyana', b'Guyana'), (b'America/Halifax', b'Halifax'), (b'America/Havana', b'Havana'), (b'America/Hermosillo', b'Hermosillo'), (b'America/Indiana/Indianapolis', b'Indiana/Indianapolis'), (b'America/Indiana/Knox', b'Indiana/Knox'), (b'America/Indiana/Marengo', b'Indiana/Marengo'), (b'America/Indiana/Petersburg', b'Indiana/Petersburg'), (b'America/Indiana/Tell_City', b'Indiana/Tell_City'), (b'America/Indiana/Vevay', b'Indiana/Vevay'), (b'America/Indiana/Vincennes', b'Indiana/Vincennes'), (b'America/Indiana/Winamac', b'Indiana/Winamac'), (b'America/Indianapolis', b'Indianapolis'), (b'America/Inuvik', b'Inuvik'), (b'America/Iqaluit', b'Iqaluit'), (b'America/Jamaica', b'Jamaica'), (b'America/Jujuy', b'Jujuy'), (b'America/Juneau', b'Juneau'), (b'America/Kentucky/Louisville', b'Kentucky/Louisville'), (b'America/Kentucky/Monticello', b'Kentucky/Monticello'), (b'America/Knox_IN', b'Knox_IN'), (b'America/Kralendijk', b'Kralendijk'), (b'America/La_Paz', b'La_Paz'), (b'America/Lima', b'Lima'), (b'America/Los_Angeles', b'Los_Angeles'), (b'America/Louisville', b'Louisville'), (b'America/Lower_Princes', b'Lower_Princes'), (b'America/Maceio', b'Maceio'), (b'America/Managua', b'Managua'), (b'America/Manaus', b'Manaus'), (b'America/Marigot', b'Marigot'), (b'America/Martinique', b'Martinique'), (b'America/Matamoros', b'Matamoros'), (b'America/Mazatlan', b'Mazatlan'), (b'America/Mendoza', b'Mendoza'), (b'America/Menominee', b'Menominee'), (b'America/Merida', b'Merida'), (b'America/Metlakatla', b'Metlakatla'), (b'America/Mexico_City', b'Mexico_City'), (b'America/Miquelon', b'Miquelon'), (b'America/Moncton', b'Moncton'), (b'America/Monterrey', b'Monterrey'), (b'America/Montevideo', b'Montevideo'), (b'America/Montreal', b'Montreal'), (b'America/Montserrat', b'Montserrat'), (b'America/Nassau', b'Nassau'), (b'America/New_York', b'New_York'), (b'America/Nipigon', b'Nipigon'), (b'America/Nome', b'Nome'), (b'America/Noronha', b'Noronha'), (b'America/North_Dakota/Beulah', b'North_Dakota/Beulah'), (b'America/North_Dakota/Center', b'North_Dakota/Center'), (b'America/North_Dakota/New_Salem', b'North_Dakota/New_Salem'), (b'America/Ojinaga', b'Ojinaga'), (b'America/Panama', b'Panama'), (b'America/Pangnirtung', b'Pangnirtung'), (b'America/Paramaribo', b'Paramaribo'), (b'America/Phoenix', b'Phoenix'), (b'America/Port-au-Prince', b'Port-au-Prince'), (b'America/Port_of_Spain', b'Port_of_Spain'), (b'America/Porto_Acre', b'Porto_Acre'), (b'America/Porto_Velho', b'Porto_Velho'), (b'America/Puerto_Rico', b'Puerto_Rico'), (b'America/Rainy_River', b'Rainy_River'), (b'America/Rankin_Inlet', b'Rankin_Inlet'), (b'America/Recife', b'Recife'), (b'America/Regina', b'Regina'), (b'America/Resolute', b'Resolute'), (b'America/Rio_Branco', b'Rio_Branco'), (b'America/Rosario', b'Rosario'), (b'America/Santa_Isabel', b'Santa_Isabel'), (b'America/Santarem', b'Santarem'), (b'America/Santiago', b'Santiago'), (b'America/Santo_Domingo', b'Santo_Domingo'), (b'America/Sao_Paulo', b'Sao_Paulo'), (b'America/Scoresbysund', b'Scoresbysund'), (b'America/Shiprock', b'Shiprock'), (b'America/Sitka', b'Sitka'), (b'America/St_Barthelemy', b'St_Barthelemy'), (b'America/St_Johns', b'St_Johns'), (b'America/St_Kitts', b'St_Kitts'), (b'America/St_Lucia', b'St_Lucia'), (b'America/St_Thomas', b'St_Thomas'), (b'America/St_Vincent', b'St_Vincent'), (b'America/Swift_Current', b'Swift_Current'), (b'America/Tegucigalpa', b'Tegucigalpa'), (b'America/Thule', b'Thule'), (b'America/Thunder_Bay', b'Thunder_Bay'), (b'America/Tijuana', b'Tijuana'), (b'America/Toronto', b'Toronto'), (b'America/Tortola', b'Tortola'), (b'America/Vancouver', b'Vancouver'), (b'America/Virgin', b'Virgin'), (b'America/Whitehorse', b'Whitehorse'), (b'America/Winnipeg', b'Winnipeg'), (b'America/Yakutat', b'Yakutat'), (b'America/Yellowknife', b'Yellowknife')]), (b'Antarctica', [(b'Antarctica/Casey', b'Casey'), (b'Antarctica/Davis', b'Davis'), (b'Antarctica/DumontDUrville', b'DumontDUrville'), (b'Antarctica/Macquarie', b'Macquarie'), (b'Antarctica/Mawson', b'Mawson'), (b'Antarctica/McMurdo', b'McMurdo'), (b'Antarctica/Palmer', b'Palmer'), (b'Antarctica/Rothera', b'Rothera'), (b'Antarctica/South_Pole', b'South_Pole'), (b'Antarctica/Syowa', b'Syowa'), (b'Antarctica/Troll', b'Troll'), (b'Antarctica/Vostok', b'Vostok')]), (b'Arctic', [(b'Arctic/Longyearbyen', b'Longyearbyen')]), (b'Asia', [(b'Asia/Aden', b'Aden'), (b'Asia/Almaty', b'Almaty'), (b'Asia/Amman', b'Amman'), (b'Asia/Anadyr', b'Anadyr'), (b'Asia/Aqtau', b'Aqtau'), (b'Asia/Aqtobe', b'Aqtobe'), (b'Asia/Ashgabat', b'Ashgabat'), (b'Asia/Ashkhabad', b'Ashkhabad'), (b'Asia/Baghdad', b'Baghdad'), (b'Asia/Bahrain', b'Bahrain'), (b'Asia/Baku', b'Baku'), (b'Asia/Bangkok', b'Bangkok'), (b'Asia/Beirut', b'Beirut'), (b'Asia/Bishkek', b'Bishkek'), (b'Asia/Brunei', b'Brunei'), (b'Asia/Calcutta', b'Calcutta'), (b'Asia/Chita', b'Chita'), (b'Asia/Choibalsan', b'Choibalsan'), (b'Asia/Chongqing', b'Chongqing'), (b'Asia/Chungking', b'Chungking'), (b'Asia/Colombo', b'Colombo'), (b'Asia/Dacca', b'Dacca'), (b'Asia/Damascus', b'Damascus'), (b'Asia/Dhaka', b'Dhaka'), (b'Asia/Dili', b'Dili'), (b'Asia/Dubai', b'Dubai'), (b'Asia/Dushanbe', b'Dushanbe'), (b'Asia/Gaza', b'Gaza'), (b'Asia/Harbin', b'Harbin'), (b'Asia/Hebron', b'Hebron'), (b'Asia/Ho_Chi_Minh', b'Ho_Chi_Minh'), (b'Asia/Hong_Kong', b'Hong_Kong'), (b'Asia/Hovd', b'Hovd'), (b'Asia/Irkutsk', b'Irkutsk'), (b'Asia/Istanbul', b'Istanbul'), (b'Asia/Jakarta', b'Jakarta'), (b'Asia/Jayapura', b'Jayapura'), (b'Asia/Jerusalem', b'Jerusalem'), (b'Asia/Kabul', b'Kabul'), (b'Asia/Kamchatka', b'Kamchatka'), (b'Asia/Karachi', b'Karachi'), (b'Asia/Kashgar', b'Kashgar'), (b'Asia/Kathmandu', b'Kathmandu'), (b'Asia/Katmandu', b'Katmandu'), (b'Asia/Khandyga', b'Khandyga'), (b'Asia/Kolkata', b'Kolkata'), (b'Asia/Krasnoyarsk', b'Krasnoyarsk'), (b'Asia/Kuala_Lumpur', b'Kuala_Lumpur'), (b'Asia/Kuching', b'Kuching'), (b'Asia/Kuwait', b'Kuwait'), (b'Asia/Macao', b'Macao'), (b'Asia/Macau', b'Macau'), (b'Asia/Magadan', b'Magadan'), (b'Asia/Makassar', b'Makassar'), (b'Asia/Manila', b'Manila'), (b'Asia/Muscat', b'Muscat'), (b'Asia/Nicosia', b'Nicosia'), (b'Asia/Novokuznetsk', b'Novokuznetsk'), (b'Asia/Novosibirsk', b'Novosibirsk'), (b'Asia/Omsk', b'Omsk'), (b'Asia/Oral', b'Oral'), (b'Asia/Phnom_Penh', b'Phnom_Penh'), (b'Asia/Pontianak', b'Pontianak'), (b'Asia/Pyongyang', b'Pyongyang'), (b'Asia/Qatar', b'Qatar'), (b'Asia/Qyzylorda', b'Qyzylorda'), (b'Asia/Rangoon', b'Rangoon'), (b'Asia/Riyadh', b'Riyadh'), (b'Asia/Saigon', b'Saigon'), (b'Asia/Sakhalin', b'Sakhalin'), (b'Asia/Samarkand', b'Samarkand'), (b'Asia/Seoul', b'Seoul'), (b'Asia/Shanghai', b'Shanghai'), (b'Asia/Singapore', b'Singapore'), (b'Asia/Srednekolymsk', b'Srednekolymsk'), (b'Asia/Taipei', b'Taipei'), (b'Asia/Tashkent', b'Tashkent'), (b'Asia/Tbilisi', b'Tbilisi'), (b'Asia/Tehran', b'Tehran'), (b'Asia/Tel_Aviv', b'Tel_Aviv'), (b'Asia/Thimbu', b'Thimbu'), (b'Asia/Thimphu', b'Thimphu'), (b'Asia/Tokyo', b'Tokyo'), (b'Asia/Ujung_Pandang', b'Ujung_Pandang'), (b'Asia/Ulaanbaatar', b'Ulaanbaatar'), (b'Asia/Ulan_Bator', b'Ulan_Bator'), (b'Asia/Urumqi', b'Urumqi'), (b'Asia/Ust-Nera', b'Ust-Nera'), (b'Asia/Vientiane', b'Vientiane'), (b'Asia/Vladivostok', b'Vladivostok'), (b'Asia/Yakutsk', b'Yakutsk'), (b'Asia/Yekaterinburg', b'Yekaterinburg'), (b'Asia/Yerevan', b'Yerevan')]), (b'Atlantic', [(b'Atlantic/Azores', b'Azores'), (b'Atlantic/Bermuda', b'Bermuda'), (b'Atlantic/Canary', b'Canary'), (b'Atlantic/Cape_Verde', b'Cape_Verde'), (b'Atlantic/Faeroe', b'Faeroe'), (b'Atlantic/Faroe', b'Faroe'), (b'Atlantic/Jan_Mayen', b'Jan_Mayen'), (b'Atlantic/Madeira', b'Madeira'), (b'Atlantic/Reykjavik', b'Reykjavik'), (b'Atlantic/South_Georgia', b'South_Georgia'), (b'Atlantic/St_Helena', b'St_Helena'), (b'Atlantic/Stanley', b'Stanley')]), (b'Australia', [(b'Australia/ACT', b'ACT'), (b'Australia/Adelaide', b'Adelaide'), (b'Australia/Brisbane', b'Brisbane'), (b'Australia/Broken_Hill', b'Broken_Hill'), (b'Australia/Canberra', b'Canberra'), (b'Australia/Currie', b'Currie'), (b'Australia/Darwin', b'Darwin'), (b'Australia/Eucla', b'Eucla'), (b'Australia/Hobart', b'Hobart'), (b'Australia/LHI', b'LHI'), (b'Australia/Lindeman', b'Lindeman'), (b'Australia/Lord_Howe', b'Lord_Howe'), (b'Australia/Melbourne', b'Melbourne'), (b'Australia/NSW', b'NSW'), (b'Australia/North', b'North'), (b'Australia/Perth', b'Perth'), (b'Australia/Queensland', b'Queensland'), (b'Australia/South', b'South'), (b'Australia/Sydney', b'Sydney'), (b'Australia/Tasmania', b'Tasmania'), (b'Australia/Victoria', b'Victoria'), (b'Australia/West', b'West'), (b'Australia/Yancowinna', b'Yancowinna')]), (b'Brazil', [(b'Brazil/Acre', b'Acre'), (b'Brazil/DeNoronha', b'DeNoronha'), (b'Brazil/East', b'East'), (b'Brazil/West', b'West')]), (b'Canada', [(b'Canada/Atlantic', b'Atlantic'), (b'Canada/Central', b'Central'), (b'Canada/East-Saskatchewan', b'East-Saskatchewan'), (b'Canada/Eastern', b'Eastern'), (b'Canada/Mountain', b'Mountain'), (b'Canada/Newfoundland', b'Newfoundland'), (b'Canada/Pacific', b'Pacific'), (b'Canada/Saskatchewan', b'Saskatchewan'), (b'Canada/Yukon', b'Yukon')]), (b'Chile', [(b'Chile/Continental', b'Continental'), (b'Chile/EasterIsland', b'EasterIsland')]), (b'Etc', [(b'Etc/Greenwich', b'Greenwich'), (b'Etc/UCT', b'UCT'), (b'Etc/UTC', b'UTC'), (b'Etc/Universal', b'Universal'), (b'Etc/Zulu', b'Zulu')]), (b'Europe', [(b'Europe/Amsterdam', b'Amsterdam'), (b'Europe/Andorra', b'Andorra'), (b'Europe/Athens', b'Athens'), (b'Europe/Belfast', b'Belfast'), (b'Europe/Belgrade', b'Belgrade'), (b'Europe/Berlin', b'Berlin'), (b'Europe/Bratislava', b'Bratislava'), (b'Europe/Brussels', b'Brussels'), (b'Europe/Bucharest', b'Bucharest'), (b'Europe/Budapest', b'Budapest'), (b'Europe/Busingen', b'Busingen'), (b'Europe/Chisinau', b'Chisinau'), (b'Europe/Copenhagen', b'Copenhagen'), (b'Europe/Dublin', b'Dublin'), (b'Europe/Gibraltar', b'Gibraltar'), (b'Europe/Guernsey', b'Guernsey'), (b'Europe/Helsinki', b'Helsinki'), (b'Europe/Isle_of_Man', b'Isle_of_Man'), (b'Europe/Istanbul', b'Istanbul'), (b'Europe/Jersey', b'Jersey'), (b'Europe/Kaliningrad', b'Kaliningrad'), (b'Europe/Kiev', b'Kiev'), (b'Europe/Lisbon', b'Lisbon'), (b'Europe/Ljubljana', b'Ljubljana'), (b'Europe/London', b'London'), (b'Europe/Luxembourg', b'Luxembourg'), (b'Europe/Madrid', b'Madrid'), (b'Europe/Malta', b'Malta'), (b'Europe/Mariehamn', b'Mariehamn'), (b'Europe/Minsk', b'Minsk'), (b'Europe/Monaco', b'Monaco'), (b'Europe/Moscow', b'Moscow'), (b'Europe/Nicosia', b'Nicosia'), (b'Europe/Oslo', b'Oslo'), (b'Europe/Paris', b'Paris'), (b'Europe/Podgorica', b'Podgorica'), (b'Europe/Prague', b'Prague'), (b'Europe/Riga', b'Riga'), (b'Europe/Rome', b'Rome'), (b'Europe/Samara', b'Samara'), (b'Europe/San_Marino', b'San_Marino'), (b'Europe/Sarajevo', b'Sarajevo'), (b'Europe/Simferopol', b'Simferopol'), (b'Europe/Skopje', b'Skopje'), (b'Europe/Sofia', b'Sofia'), (b'Europe/Stockholm', b'Stockholm'), (b'Europe/Tallinn', b'Tallinn'), (b'Europe/Tirane', b'Tirane'), (b'Europe/Tiraspol', b'Tiraspol'), (b'Europe/Uzhgorod', b'Uzhgorod'), (b'Europe/Vaduz', b'Vaduz'), (b'Europe/Vatican', b'Vatican'), (b'Europe/Vienna', b'Vienna'), (b'Europe/Vilnius', b'Vilnius'), (b'Europe/Volgograd', b'Volgograd'), (b'Europe/Warsaw', b'Warsaw'), (b'Europe/Zagreb', b'Zagreb'), (b'Europe/Zaporozhye', b'Zaporozhye'), (b'Europe/Zurich', b'Zurich')]), (b'Indian', [(b'Indian/Antananarivo', b'Antananarivo'), (b'Indian/Chagos', b'Chagos'), (b'Indian/Christmas', b'Christmas'), (b'Indian/Cocos', b'Cocos'), (b'Indian/Comoro', b'Comoro'), (b'Indian/Kerguelen', b'Kerguelen'), (b'Indian/Mahe', b'Mahe'), (b'Indian/Maldives', b'Maldives'), (b'Indian/Mauritius', b'Mauritius'), (b'Indian/Mayotte', b'Mayotte'), (b'Indian/Reunion', b'Reunion')]), (b'Mexico', [(b'Mexico/BajaNorte', b'BajaNorte'), (b'Mexico/BajaSur', b'BajaSur'), (b'Mexico/General', b'General')]), (b'Other', [(b'CET', b'CET'), (b'CST6CDT', b'CST6CDT'), (b'Cuba', b'Cuba'), (b'EET', b'EET'), (b'EST', b'EST'), (b'EST5EDT', b'EST5EDT'), (b'Egypt', b'Egypt'), (b'Eire', b'Eire'), (b'GB', b'GB'), (b'GB-Eire', b'GB-Eire'), (b'Greenwich', b'Greenwich'), (b'HST', b'HST'), (b'Hongkong', b'Hongkong'), (b'Iceland', b'Iceland'), (b'Iran', b'Iran'), (b'Israel', b'Israel'), (b'Jamaica', b'Jamaica'), (b'Japan', b'Japan'), (b'Kwajalein', b'Kwajalein'), (b'Libya', b'Libya'), (b'MET', b'MET'), (b'MST', b'MST'), (b'MST7MDT', b'MST7MDT'), (b'NZ', b'NZ'), (b'NZ-CHAT', b'NZ-CHAT'), (b'Navajo', b'Navajo'), (b'PRC', b'PRC'), (b'PST8PDT', b'PST8PDT'), (b'Poland', b'Poland'), (b'Portugal', b'Portugal'), (b'ROC', b'ROC'), (b'ROK', b'ROK'), (b'Singapore', b'Singapore'), (b'Turkey', b'Turkey'), (b'UCT', b'UCT'), (b'UTC', b'UTC'), (b'Universal', b'Universal'), (b'W-SU', b'W-SU'), (b'WET', b'WET'), (b'Zulu', b'Zulu')]), (b'Pacific', [(b'Pacific/Apia', b'Apia'), (b'Pacific/Auckland', b'Auckland'), (b'Pacific/Chatham', b'Chatham'), (b'Pacific/Chuuk', b'Chuuk'), (b'Pacific/Easter', b'Easter'), (b'Pacific/Efate', b'Efate'), (b'Pacific/Enderbury', b'Enderbury'), (b'Pacific/Fakaofo', b'Fakaofo'), (b'Pacific/Fiji', b'Fiji'), (b'Pacific/Funafuti', b'Funafuti'), (b'Pacific/Galapagos', b'Galapagos'), (b'Pacific/Gambier', b'Gambier'), (b'Pacific/Guadalcanal', b'Guadalcanal'), (b'Pacific/Guam', b'Guam'), (b'Pacific/Honolulu', b'Honolulu'), (b'Pacific/Johnston', b'Johnston'), (b'Pacific/Kiritimati', b'Kiritimati'), (b'Pacific/Kosrae', b'Kosrae'), (b'Pacific/Kwajalein', b'Kwajalein'), (b'Pacific/Majuro', b'Majuro'), (b'Pacific/Marquesas', b'Marquesas'), (b'Pacific/Midway', b'Midway'), (b'Pacific/Nauru', b'Nauru'), (b'Pacific/Niue', b'Niue'), (b'Pacific/Norfolk', b'Norfolk'), (b'Pacific/Noumea', b'Noumea'), (b'Pacific/Pago_Pago', b'Pago_Pago'), (b'Pacific/Palau', b'Palau'), (b'Pacific/Pitcairn', b'Pitcairn'), (b'Pacific/Pohnpei', b'Pohnpei'), (b'Pacific/Ponape', b'Ponape'), (b'Pacific/Port_Moresby', b'Port_Moresby'), (b'Pacific/Rarotonga', b'Rarotonga'), (b'Pacific/Saipan', b'Saipan'), (b'Pacific/Samoa', b'Samoa'), (b'Pacific/Tahiti', b'Tahiti'), (b'Pacific/Tarawa', b'Tarawa'), (b'Pacific/Tongatapu', b'Tongatapu'), (b'Pacific/Truk', b'Truk'), (b'Pacific/Wake', b'Wake'), (b'Pacific/Wallis', b'Wallis'), (b'Pacific/Yap', b'Yap')]), (b'US', [(b'US/Alaska', b'Alaska'), (b'US/Aleutian', b'Aleutian'), (b'US/Arizona', b'Arizona'), (b'US/Central', b'Central'), (b'US/East-Indiana', b'East-Indiana'), (b'US/Eastern', b'Eastern'), (b'US/Hawaii', b'Hawaii'), (b'US/Indiana-Starke', b'Indiana-Starke'), (b'US/Michigan', b'Michigan'), (b'US/Mountain', b'Mountain'), (b'US/Pacific', b'Pacific'), (b'US/Pacific-New', b'Pacific-New'), (b'US/Samoa', b'Samoa')])])),
                ('points', models.FloatField(default=0, db_index=True)),
                ('ace_theme', models.CharField(default=b'github', max_length=30, choices=[(b'ambiance', b'Ambiance'), (b'chaos', b'Chaos'), (b'chrome', b'Chrome'), (b'clouds', b'Clouds'), (b'clouds_midnight', b'Clouds Midnight'), (b'cobalt', b'Cobalt'), (b'crimson_editor', b'Crimson Editor'), (b'dawn', b'Dawn'), (b'dreamweaver', b'Dreamweaver'), (b'eclipse', b'Eclipse'), (b'github', b'Github'), (b'idle_fingers', b'Idle Fingers'), (b'katzenmilch', b'Katzenmilch'), (b'kr_theme', b'KR Theme'), (b'kuroir', b'Kuroir'), (b'merbivore', b'Merbivore'), (b'merbivore_soft', b'Merbivore Soft'), (b'mono_industrial', b'Mono Industrial'), (b'monokai', b'Monokai'), (b'pastel_on_dark', b'Pastel on Dark'), (b'solarized_dark', b'Solarized Dark'), (b'solarized_light', b'Solarized Light'), (b'terminal', b'Terminal'), (b'textmate', b'Textmate'), (b'tomorrow', b'Tomorrow'), (b'tomorrow_night', b'Tomorrow Night'), (b'tomorrow_night_blue', b'Tomorrow Night Blue'), (b'tomorrow_night_bright', b'Tomorrow Night Bright'), (b'tomorrow_night_eighties', b'Tomorrow Night Eighties'), (b'twilight', b'Twilight'), (b'vibrant_ink', b'Vibrant Ink'), (b'xcode', b'XCode')])),
                ('last_access', models.DateTimeField(default=django.utils.timezone.now, verbose_name=b'Last access time')),
                ('ip', models.GenericIPAddressField(null=True, verbose_name=b'Last IP', blank=True)),
                ('organization_join_time', models.DateTimeField(null=True, verbose_name=b'Organization joining date', blank=True)),
                ('display_rank', models.CharField(default=b'user', max_length=10, choices=[(b'user', b'Normal User'), (b'setter', b'Problem Setter'), (b'admin', b'Admin')])),
                ('mute', models.BooleanField(default=False, help_text=b'Some users are at their best when silent.', verbose_name=b'Comment mute')),
                ('rating', models.IntegerField(default=None, null=True)),
                ('language', models.ForeignKey(verbose_name=b'Preferred language', to='judge.Language')),
                ('organization', models.ForeignKey(related_query_name=b'member', related_name='members', on_delete=django.db.models.deletion.SET_NULL, verbose_name=b'Organization', blank=True, to='judge.Organization', null=True)),
                ('user', models.OneToOneField(verbose_name=b'User associated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rank', models.IntegerField()),
                ('rating', models.IntegerField()),
                ('volatility', models.IntegerField()),
                ('last_rated', models.DateTimeField(db_index=True)),
                ('contest', models.ForeignKey(related_name='ratings', to='judge.Contest')),
                ('participation', models.OneToOneField(related_name='rating', to='judge.ContestParticipation')),
                ('user', models.ForeignKey(related_name='ratings', to='judge.Profile')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Solution',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.CharField(db_index=True, max_length=100, verbose_name=b'URL', blank=True)),
                ('title', models.CharField(max_length=200)),
                ('is_public', models.BooleanField()),
                ('publish_on', models.DateTimeField()),
                ('content', models.TextField()),
                ('authors', models.ManyToManyField(to='judge.Profile', blank=True)),
            ],
            options={
                'permissions': (('see_private_solution', 'See hidden solutions'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name=b'Submission time')),
                ('time', models.FloatField(null=True, verbose_name=b'Execution time', db_index=True)),
                ('memory', models.FloatField(null=True, verbose_name=b'Memory usage')),
                ('points', models.FloatField(null=True, verbose_name=b'Points granted', db_index=True)),
                ('source', models.TextField(max_length=65536, verbose_name=b'Source code')),
                ('status', models.CharField(default=b'QU', max_length=2, db_index=True, choices=[(b'QU', b'Queued'), (b'P', b'Processing'), (b'G', b'Grading'), (b'D', b'Completed'), (b'IE', b'Internal Error'), (b'CE', b'Compile Error'), (b'AB', b'Aborted')])),
                ('result', models.CharField(default=None, choices=[(b'AC', b'Accepted'), (b'WA', b'Wrong Answer'), (b'TLE', b'Time Limit Exceeded'), (b'MLE', b'Memory Limit Exceeded'), (b'OLE', b'Output Limit Exceeded'), (b'IR', b'Invalid Return'), (b'RTE', b'Runtime Error'), (b'CE', b'Compile Error'), (b'IE', b'Internal Error'), (b'SC', b'Short circuit'), (b'AB', b'Aborted')], max_length=3, blank=True, null=True, db_index=True)),
                ('error', models.TextField(null=True, verbose_name=b'Compile Errors', blank=True)),
                ('current_testcase', models.IntegerField(default=0)),
                ('batch', models.BooleanField(default=False, verbose_name=b'Batched cases')),
                ('case_points', models.FloatField(default=0, verbose_name=b'Test case points')),
                ('case_total', models.FloatField(default=0, verbose_name=b'Test case total points')),
                ('language', models.ForeignKey(verbose_name=b'Submission language', to='judge.Language')),
                ('problem', models.ForeignKey(to='judge.Problem')),
                ('user', models.ForeignKey(to='judge.Profile')),
            ],
            options={
                'permissions': (('abort_any_submission', 'Abort any submission'), ('rejudge_submission', 'Rejudge the submission'), ('rejudge_submission_lot', 'Rejudge a lot of submissions'), ('spam_submission', 'Submit without limit'), ('view_all_submission', 'View all submission'), ('resubmit_other', "Resubmit others' submission")),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubmissionTestCase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('case', models.IntegerField(verbose_name=b'Test case ID')),
                ('status', models.CharField(max_length=3, verbose_name=b'Status flag', choices=[(b'AC', b'Accepted'), (b'WA', b'Wrong Answer'), (b'TLE', b'Time Limit Exceeded'), (b'MLE', b'Memory Limit Exceeded'), (b'OLE', b'Output Limit Exceeded'), (b'IR', b'Invalid Return'), (b'RTE', b'Runtime Error'), (b'CE', b'Compile Error'), (b'IE', b'Internal Error'), (b'SC', b'Short circuit'), (b'AB', b'Aborted')])),
                ('time', models.FloatField(null=True, verbose_name=b'Execution time')),
                ('memory', models.FloatField(null=True, verbose_name=b'Memory usage')),
                ('points', models.FloatField(null=True, verbose_name=b'Points granted')),
                ('total', models.FloatField(null=True, verbose_name=b'Points possible')),
                ('batch', models.IntegerField(null=True, verbose_name=b'Batch number')),
                ('feedback', models.CharField(max_length=50, verbose_name=b'Judging feedback', blank=True)),
                ('output', models.TextField(verbose_name=b'Program output', blank=True)),
                ('submission', models.ForeignKey(related_name='test_cases', verbose_name=b'Associated submission', to='judge.Submission')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='rating',
            unique_together=set([('user', 'contest')]),
        ),
        migrations.AddField(
            model_name='problem',
            name='authors',
            field=models.ManyToManyField(related_name='authored_problems', verbose_name=b'Creators', to='judge.Profile', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='problem',
            name='banned_users',
            field=models.ManyToManyField(help_text=b'Bans the selected users from submitting to this problem', to='judge.Profile', verbose_name=b'Personae non gratae', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='problem',
            name='group',
            field=models.ForeignKey(verbose_name=b'Problem group', to='judge.ProblemGroup'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='problem',
            name='types',
            field=models.ManyToManyField(to='judge.ProblemType', verbose_name=b'Problem types'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='privatemessage',
            name='sender',
            field=models.ForeignKey(related_name='sent_messages', verbose_name=b'Sender', to='judge.Profile'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='privatemessage',
            name='target',
            field=models.ForeignKey(related_name='received_messages', verbose_name=b'Target', to='judge.Profile'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='organization',
            name='admins',
            field=models.ManyToManyField(help_text=b'Those who can edit this organization', related_name='+', verbose_name=b'Administrators', to='judge.Profile'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='organization',
            name='registrant',
            field=models.ForeignKey(related_name='registrant+', verbose_name=b'Registrant', to='judge.Profile', help_text=b'User who registered this organization'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='judge',
            name='problems',
            field=models.ManyToManyField(related_name='judges', to='judge.Problem'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='judge',
            name='runtimes',
            field=models.ManyToManyField(related_name='judges', to='judge.Language'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contestsubmission',
            name='submission',
            field=models.OneToOneField(related_name='contest', to='judge.Submission'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contestprofile',
            name='user',
            field=models.OneToOneField(related_query_name=b'contest', related_name='contest_profile', verbose_name=b'User', to='judge.Profile'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contestproblem',
            name='problem',
            field=models.ForeignKey(related_name='contests', to='judge.Problem'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='contestproblem',
            unique_together=set([('problem', 'contest')]),
        ),
        migrations.AddField(
            model_name='contestparticipation',
            name='profile',
            field=models.ForeignKey(related_name='history', verbose_name=b'User', to='judge.ContestProfile'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contest',
            name='organizers',
            field=models.ManyToManyField(help_text=b'These people will be able to edit the contest.', related_name='organizers+', to='judge.Profile'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contest',
            name='problems',
            field=models.ManyToManyField(to='judge.Problem', verbose_name=b'Problems', through='judge.ContestProblem'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contest',
            name='rate_exclude',
            field=models.ManyToManyField(related_name='rate_exclude+', verbose_name=b'exclude from ratings', to='judge.Profile', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='commentvote',
            name='voter',
            field=models.ForeignKey(to='judge.Profile'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='commentvote',
            unique_together=set([('voter', 'comment')]),
        ),
        migrations.AddField(
            model_name='comment',
            name='author',
            field=models.ForeignKey(verbose_name=b'Commenter', to='judge.Profile'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='comment',
            name='parent',
            field=mptt.fields.TreeForeignKey(related_name='replies', blank=True, to='judge.Comment', null=True),
            preserve_default=True,
        ),
    ]
