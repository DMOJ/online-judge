from django.contrib.auth.models import User
from django.db import models
from django.contrib import admin

LANGUAGES = (
    ('PY', 'Python'),
    ('CPP', 'C++'),
)


class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name='The user whom this profile is associated with')
    name = models.CharField(max_length=50, verbose_name="User's long name, real or not", null=True)
    about = models.TextField(verbose_name="User's self description", null=True)
    timezone = models.CharField(max_length=50, verbose_name="User's timezone", default='UTC')
    language = models.CharField(max_length=50, verbose_name="User's default language", choices=LANGUAGES, default='PY')

    def __unicode__(self):
        return u'Profile of %s (%s) in %s speaking %s' % (self.user.username, self.name, self.timezone, self.language)


class ProfileAdmin(admin.ModelAdmin):
    fields = ['user', 'name', 'about', 'timezone', 'language']


class ProblemType(models.Model):
    name = models.CharField(max_length=20, verbose_name='Problem category ID')
    full_name = models.CharField(max_length=100, verbose_name='Problem category name')


class Problem(models.Model):
    name = models.CharField(max_length=100, verbose_name='Problem name')
    description = models.TextField(verbose_name='Problem body')
    user = models.ForeignKey(Profile, verbose_name='Creator')
    category = models.ManyToManyField(ProblemType, verbose_name='Type of problem')
    time_limit = models.FloatField(verbose_name='Time limit for execution')
    memory_limit = models.FloatField(verbose_name='Memory limit')
    points = models.FloatField(verbose_name='Points this problem is worth')
    partial = models.BooleanField(verbose_name='Whether partial points are allowed')


class Comment(models.Model):
    user = models.ForeignKey(Profile, verbose_name='User who posted this comment')
    problem = models.ForeignKey(Problem, null=True, verbose_name='Problem this comment is associated with')
    title = models.CharField(max_length=200, verbose_name='Title of comment')
    body = models.TextField(verbose_name='Body of comment')


class Submission(models.Model):
    user = models.ForeignKey(Profile)
    problem = models.ForeignKey(Problem)
    time = models.FloatField(verbose_name='Execution time', null=True)
    memory = models.FloatField(verbose_name='Memory usage', null=True)
    points = models.FloatField(verbose_name='Points granted', null=True)

admin.site.register(Profile, ProfileAdmin)
