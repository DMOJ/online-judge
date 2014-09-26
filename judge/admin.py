from django.contrib import admin, messages
from django.conf.urls import patterns, url
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import TextField
from django.forms import ModelForm, ModelMultipleChoiceField, TextInput
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from judge.models import Language, Profile, Problem, ProblemGroup, ProblemType, Submission, Comment, GraderType, \
    MiscConfig, Judge
from judge.widgets import CheckboxSelectMultipleWithSelectAll


try:
    from pagedown.widgets import AdminPagedownWidget
except ImportError:
    AdminPagedownWidget = None


class ProfileAdmin(admin.ModelAdmin):
    fields = ['user', 'name', 'about', 'timezone', 'language', 'ace_theme']
    list_display = ['long_display_name', 'timezone_full', 'language']
    ordering = ['user__username']

    def timezone_full(self, obj):
        return obj.timezone
    timezone_full.admin_order_field = 'timezone'
    timezone_full.short_description = 'Timezone'


class ProblemAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('code', 'name', 'user', 'description', 'types', 'groups')}),
        ('Points', {'fields': (('points', 'partial'), 'short_circuit', 'grader', 'grader_param')}),
        ('Limits', {'fields': ('time_limit', 'memory_limit')}),
        ('Language', {'fields': ('allowed_languages',)})
    )
    list_display = ['code', 'name', 'user', 'points']
    ordering = ['code']
    if AdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': AdminPagedownWidget},
        }

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'allowed_languages':
            kwargs['widget'] = CheckboxSelectMultipleWithSelectAll()
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
            url(r'^(\d+)/judge/$', self.judge_view, name='judge_submission_rejudge'),
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


class CommentAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('author', 'page', 'parent', 'score')}),
        ('Content', {'fields': ('title', 'body')}),
    )
    list_display = ['title', 'author', 'page', 'time']
    if AdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': AdminPagedownWidget},
        }


class LanguageForm(ModelForm):
    problems = ModelMultipleChoiceField(
        label='Allowed problems',
        queryset=Problem.objects.all(),
        required=False,
        help_text='These problems are allowed to be submitted in this language',
        widget=FilteredSelectMultiple('problems', False))


class LanguageAdmin(admin.ModelAdmin):
    fields = ('key', 'name', 'ace', 'problems')
    form = LanguageForm

    def save_model(self, request, obj, form, change):
        super(LanguageAdmin, self).save_model(request, obj, form, change)
        obj.problem_set.clear()
        for problem in form.cleaned_data['problems']:
            obj.problem_set.add(problem)

    def get_form(self, request, obj=None, **kwargs):
        self.form.base_fields['problems'].initial = [o.pk for o in obj.problem_set.all()] if obj else []
        return super(LanguageAdmin, self).get_form(request, obj, **kwargs)


class ProblemGroupForm(ModelForm):
    problems = ModelMultipleChoiceField(
        label='Included problems',
        queryset=Problem.objects.all(),
        required=False,
        help_text='These problems are included in this group of problems',
        widget=FilteredSelectMultiple('problems', False))


class ProblemGroupAdmin(admin.ModelAdmin):
    fields = ('name', 'full_name', 'problems')
    form = ProblemGroupForm

    def save_model(self, request, obj, form, change):
        super(ProblemGroupAdmin, self).save_model(request, obj, form, change)
        obj.problem_set.clear()
        for problem in form.cleaned_data['problems']:
            obj.problem_set.add(problem)

    def get_form(self, request, obj=None, **kwargs):
        self.form.base_fields['problems'].initial = [o.pk for o in obj.problem_set.all()] if obj else []
        return super(ProblemGroupAdmin, self).get_form(request, obj, **kwargs)


class ProblemTypeForm(ModelForm):
    problems = ModelMultipleChoiceField(
        label='Included problems',
        queryset=Problem.objects.all(),
        required=False,
        help_text='These problems are included in this type of problems',
        widget=FilteredSelectMultiple('problems', False))


class ProblemTypeAdmin(admin.ModelAdmin):
    fields = ('name', 'full_name', 'problems')
    form = ProblemTypeForm

    def save_model(self, request, obj, form, change):
        super(ProblemTypeAdmin, self).save_model(request, obj, form, change)
        obj.problem_set.clear()
        for problem in form.cleaned_data['problems']:
            obj.problem_set.add(problem)

    def get_form(self, request, obj=None, **kwargs):
        self.form.base_fields['problems'].initial = [o.pk for o in obj.problem_set.all()] if obj else []
        return super(ProblemTypeAdmin, self).get_form(request, obj, **kwargs)


class GenerateKeyTextInput(TextInput):
    def render(self, name, value, attrs=None):
        text = super(TextInput, self).render(name, value, attrs)
        return mark_safe(text + format_html(
            '''\
<a href="#" onclick="return false;" class="button" id="id_{0}_regen">Regenerate</a>
<script type="text/javascript">
(function ($) {{
    $(document).ready(function () {{
        $('#id_{0}_regen').click(function () {{
            var length = 100,
                charset = "abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`~!@#$%^&*()_+-=|[]{{}};:,<>./?",
                key = "";
            for (var i = 0, n = charset.length; i < length; ++i) {{
                key += charset.charAt(Math.floor(Math.random() * n));
            }}
            $('#id_{0}').val(key);
        }});
    }});
}})(django.jQuery);
</script>
''', name))


class JudgeAdminForm(ModelForm):
    class Meta:
        model = Judge
        widgets = {
            'auth_key': GenerateKeyTextInput(),
        }


class JudgeAdmin(admin.ModelAdmin):
    form = JudgeAdminForm
    readonly_fields = ('created', 'online', 'last_connect', 'ping', 'load', 'runtimes')
    fieldsets = (
        (None, {'fields': ('name', 'auth_key')}),
        ('Information', {'fields': ('created', 'online', 'last_connect', 'ping', 'load')}),
        ('Capabilities', {'fields': ('runtimes',)}),
    )
    list_display = ('name', 'online', 'last_connect', 'ping', 'load')
    ordering = ['name']

admin.site.register(Language, LanguageAdmin)
admin.site.register(GraderType)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Problem, ProblemAdmin)
admin.site.register(ProblemGroup, ProblemGroupAdmin)
admin.site.register(ProblemType, ProblemGroupAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(MiscConfig)
admin.site.register(Judge, JudgeAdmin)