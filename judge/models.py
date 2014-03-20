from django.conf.urls import patterns
from django.contrib.auth.models import User
from django.db import models
from django.contrib import admin, messages
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.core.exceptions import ObjectDoesNotExist
import pytz
from operator import itemgetter, attrgetter

from judge.judgeapi import judge_submission


def make_timezones():
    data = {}
    for tz in pytz.all_timezones:
        if '/' in tz:
            area, loc = tz.split('/', 1)
        else:
            area, loc = 'Other', tz
        if area in data:
            data[area].append((tz, loc))
        else:
            data[area] = [(tz, loc)]
    data = data.items()
    data.sort(key=itemgetter(0))
    return data


TIMEZONE = make_timezones()
del make_timezones


class Language(models.Model):
    key = models.CharField(max_length=6, verbose_name='Short identifier', unique=True)
    name = models.CharField(max_length=20, verbose_name='Name as shown to user')

    def __unicode__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name='User associated')
    name = models.CharField(max_length=50, verbose_name='Display name', null=True, blank=True)
    about = models.TextField(verbose_name='Self-description', null=True, blank=True)
    timezone = models.CharField(max_length=50, verbose_name='Timezone', default='UTC', choices=TIMEZONE)
    language = models.ForeignKey(Language, verbose_name='Default language')

    def display_name(self):
        if self.name:
            return self.name
        return self.user.username

    def long_display_name(self):
        if self.name:
            return u'%s (%s)' % (self.user.username, self.name)
        return self.user.username

    def __unicode__(self):
        #return u'Profile of %s in %s speaking %s' % (self.long_display_name(), self.timezone, self.language)
        return self.long_display_name()


class ProblemType(models.Model):
    name = models.CharField(max_length=20, verbose_name='Problem category ID')
    full_name = models.CharField(max_length=100, verbose_name='Problem category name')

    def __unicode__(self):
        return self.full_name


class ProblemGroup(models.Model):
    name = models.CharField(max_length=20, verbose_name='Problem group ID')
    full_name = models.CharField(max_length=100, verbose_name='Problem group name')

    def __unicode__(self):
        return self.full_name


class Problem(models.Model):
    code = models.CharField(max_length=20, verbose_name='Problem code')
    name = models.CharField(max_length=100, verbose_name='Problem name')
    description = models.TextField(verbose_name='Problem body')
    user = models.ForeignKey(Profile, verbose_name='Creator')
    types = models.ManyToManyField(ProblemType, verbose_name='Problem types')
    groups = models.ManyToManyField(ProblemGroup, verbose_name='Problem groups')
    time_limit = models.FloatField(verbose_name='Time limit')
    memory_limit = models.FloatField(verbose_name='Memory limit')
    points = models.FloatField(verbose_name='Points')
    partial = models.BooleanField(verbose_name='Allows partial points')
    allowed_languages = models.ManyToManyField(Language, verbose_name='Allowed languages')

    def types_list(self):
        return map(attrgetter('full_name'), self.types.all())

    def __unicode__(self):
        return self.name


class Comment(models.Model):
    user = models.ForeignKey(Profile, verbose_name='User who posted this comment')
    time = models.DateTimeField(verbose_name='Comment time')
    problem = models.ForeignKey(Problem, null=True, verbose_name='Associated problem')
    title = models.CharField(max_length=200, verbose_name='Title of comment')
    body = models.TextField(verbose_name='Body of comment')


SUBMISSION_RESULT = (
    ('AC', 'Accepted'),
    ('WA', 'Wrong Answer'),
    ('TLE', 'Time Limit Exceeded'),
    ('MLE', 'Memory Limit Exceeded'),
    ('IR', 'Invalid Return'),
    ('RTE', 'Runtime Error')
)


class Submission(models.Model):
    STATUS = (
        ('QU', 'Queued'),
        ('C', 'Compiled'),
        ('G', 'Grading'),
        ('D', 'Completed'),
        ('IE', 'Internal Error'),
    )

    user = models.ForeignKey(Profile)
    problem = models.ForeignKey(Problem)
    date = models.DateTimeField(verbose_name='Submission time', auto_now_add=True)
    time = models.FloatField(verbose_name='Execution time', null=True)
    memory = models.FloatField(verbose_name='Memory usage', null=True)
    points = models.FloatField(verbose_name='Points granted', null=True)
    language = models.ForeignKey(Language, verbose_name='Submission language')
    source = models.TextField(verbose_name='Source code')
    status = models.CharField(max_length=2, choices=STATUS, default='QU')
    result = models.CharField(max_length=3, choices=SUBMISSION_RESULT, default=None, null=True, blank=True)

    def judge(self):
        return judge_submission(self)

    def __unicode__(self):
        return u'Submission %d of %s by %s' % (self.id, self.problem, self.user)

    class Meta:
        permissions = (
            ('rejudge_submission', 'Rejudge the submission'),
        )


class SubmissionTestCase(models.Model):
    submission = models.ForeignKey(Submission, verbose_name='Associated submission')
    case = models.IntegerField(verbose_name='Test case ID')
    status = models.CharField(max_length=3, verbose_name='Status flag', choices=SUBMISSION_RESULT)
    time = models.FloatField(verbose_name='Execution time', null=True)
    memory = models.FloatField(verbose_name='Memory usage', null=True)
    points = models.FloatField(verbose_name='Points granted', null=True)
    total = models.FloatField(verbose_name='Points possible', null=True)


class ProfileAdmin(admin.ModelAdmin):
    fields = ['user', 'name', 'about', 'timezone', 'language']
    list_display = ['long_display_name', 'timezone_full', 'language']

    def timezone_full(self, obj):
        return obj.timezone
    timezone_full.admin_order_field = 'timezone'
    timezone_full.short_description = 'Timezone'


class ProblemAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('code', 'name', 'user', 'description', 'types', 'groups')}),
        ('Points', {'fields': (('points', 'partial'),)}),
        ('Limits', {'fields': ('time_limit', 'memory_limit')}),
    )
    list_display = ['code', 'name', 'user', 'points']


class SubmissionAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'problem', 'date')
    fields = ('user', 'problem', 'date', 'time', 'memory', 'points', 'language', 'source', 'status', 'result')
    actions = ['judge']
    list_display = ('problem_code', 'problem_name', 'user', 'execution_time', 'pretty_memory',
                    'points', 'language', 'status', 'result', 'judge_column')

    def judge(self, request, queryset):
        if not request.user.has_perm('judge.rejudge_submission'):
            self.message_user(request, 'You do not have the permission to rejudge submissions.', level=messages.ERROR)
        successful = 0
        for model in queryset:
            successful += model.judge()
        self.message_user(request, '%d submission%s were successfully rejudged.' % (successful, 's'[successful == 1:]))
    judge.short_description = 'Rejudge the selected submissions'

    def execution_time(self, obj):
        return round(obj.time, 2) if obj.time is not None else 'None'
    execution_time.admin_order_field = 'time'

    def pretty_memory(self, obj):
        memory = obj.memory
        if memory is None:
            return 'None'
        if memory < 1000:
            return '%d KB' % memory
        else:
            return '%.2f MB' % (memory / 1024.)
    pretty_memory.admin_order_field = 'memory'
    pretty_memory.short_description = 'Memory Usage'

    def problem_code(self, obj):
        return obj.problem.code

    def problem_name(self, obj):
        return obj.problem.name

    def get_urls(self):
        urls = super(SubmissionAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^(\d+)/judge/$', self.judge_view)
        )
        return my_urls + urls

    def judge_view(self, request, id):
        if not request.user.has_perm('judge.rejudge_submission'):
            return HttpResponseForbidden()
        try:
            Submission.objects.get(id=id).judge()
        except ObjectDoesNotExist:
            return Http404()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    def judge_column(self, obj):
        return '<input type="button" value="Rejudge" onclick="location.href=\'%s/judge/\'" />' % obj.id

    judge_column.short_description = ''
    judge_column.allow_tags = True


admin.site.register(Language)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Problem, ProblemAdmin)
admin.site.register(ProblemGroup)
admin.site.register(ProblemType)
admin.site.register(Submission, SubmissionAdmin)
