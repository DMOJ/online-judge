from django.contrib import admin, messages
from django.conf.urls import patterns
from django.forms import CheckboxSelectMultiple
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.core.exceptions import ObjectDoesNotExist

from judge.models import Language, Profile, Problem, ProblemGroup, ProblemType, Submission


class ProfileAdmin(admin.ModelAdmin):
    fields = ['user', 'name', 'about', 'timezone', 'language', 'ace_theme']
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
        ('Language', {'fields': ('allowed_languages',)})
    )
    list_display = ['code', 'name', 'user', 'points']

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'allowed_languages':
            kwargs['widget'] = CheckboxSelectMultiple()
        return super(ProblemAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


class SubmissionAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'problem', 'date')
    fields = ('user', 'problem', 'date', 'time', 'memory', 'points', 'language', 'source', 'status', 'result')
    actions = ['judge']
    list_display = ('id', 'problem_code', 'problem_name', 'user', 'execution_time', 'pretty_memory',
                    'points', 'language', 'status', 'result', 'judge_column')

    def judge(self, request, queryset):
        if not request.user.has_perm('judge.rejudge_submission'):
            self.message_user(request, 'You do not have the permission to rejudge submissions.', level=messages.ERROR)
            return
        successful = 0
        queryset = queryset.order_by('id')
        if queryset.count() > 10 and not request.user.has_perm('judge.rejudge_submission_lot'):
            self.message_user(request, 'You do not have the permission to rejudge THAT many submissions.',
                              level=messages.ERROR)
            return
        for model in queryset:
            successful += model.judge()
        self.message_user(request, '%d submission%s were successfully scheduled for rejudging.' %
                                   (successful, 's'[successful == 1:]))
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
            raise Http404()
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