from operator import itemgetter
from django.contrib import admin, messages
from django.conf.urls import patterns, url
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import TextField, ManyToManyField, Q
from django.forms import ModelForm, ModelMultipleChoiceField, TextInput
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from judge.models import Language, Profile, Problem, ProblemGroup, ProblemType, Submission, Comment, \
    MiscConfig, Judge, NavigationBar, Contest, ContestParticipation, ContestProblem
from judge.widgets import CheckboxSelectMultipleWithSelectAll


try:
    from pagedown.widgets import AdminPagedownWidget
except ImportError:
    AdminPagedownWidget = None


class ProfileAdmin(admin.ModelAdmin):
    fields = ('user', 'name', 'about', 'organization', 'timezone', 'language', 'ace_theme', 'last_access', 'ip')
    list_display = ('long_display_name', 'timezone_full', 'language', 'last_access', 'ip')
    ordering = ('user__username',)
    search_fields = ('user__username', 'name', 'ip')
    list_filter = ('language', 'timezone')
    actions = ('recalculate_points',)

    def timezone_full(self, obj):
        return obj.timezone
    timezone_full.admin_order_field = 'timezone'
    timezone_full.short_description = 'Timezone'

    def recalculate_points(self, request, queryset):
        count = 0
        for profile in queryset:
            profile.calculate_points()
            count += 1
        self.message_user(request, "%d user%s have scores recalculated." % (count, 's'[count == 1:]))
    recalculate_points.short_description = 'Recalculate scores'


class ProblemAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'is_public', 'user', 'description')
        }),
        ('Taxonomy', {'fields': ('types', 'group')}),
        ('Points', {'fields': (('points', 'partial'), 'short_circuit')}),
        ('Limits', {'fields': ('time_limit', 'memory_limit')}),
        ('Language', {'fields': ('allowed_languages',)})
    )
    list_display = ['code', 'name', 'user', 'points', 'is_public']
    ordering = ['code']
    search_fields = ('^code', 'name')
    actions = ['make_public', 'make_private']
    list_per_page = 500
    list_max_show_all = 1000

    if AdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': AdminPagedownWidget},
        }

    def make_public(self, request, queryset):
        count = queryset.update(is_public=True)
        self.message_user(request, "%d problem%s successfully marked as public." % (count, 's'[count == 1:]))
    make_public.short_description = 'Mark problems as public'

    def make_private(self, request, queryset):
        count = queryset.update(is_public=False)
        self.message_user(request, "%d problem%s successfully marked as private." % (count, 's'[count == 1:]))
    make_private.short_description = 'Mark problems as private'

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'allowed_languages':
            kwargs['widget'] = CheckboxSelectMultipleWithSelectAll()
        return super(ProblemAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def get_form(self, *args, **kwargs):
        form = super(ProblemAdmin, self).get_form(*args, **kwargs)
        form.base_fields['user'].queryset = Profile.objects.filter(
            Q(user__groups__name__in=['Admin', 'ProblemSetter']) |
            Q(user__is_superuser=True)
        )
        return form


class SubmissionStatusFilter(admin.SimpleListFilter):
    parameter_name = title = 'status'
    __lookups = (('None', 'None'), ('NotDone', 'Not done'), ('EX', 'Exceptional')) + Submission.STATUS
    __handles = set(map(itemgetter(0), Submission.STATUS))

    def lookups(self, request, model_admin):
        return self.__lookups

    def queryset(self, request, queryset):
        if self.value() == 'None':
            return queryset.filter(status=None)
        elif self.value() == 'NotDone':
            return queryset.exclude(status__in=['D', 'IE', 'CE', 'AB'])
        elif self.value() == 'EX':
            return queryset.exclude(status__in=['D', 'CE', 'G', 'AB'])
        elif self.value() in self.__handles:
            return queryset.filter(status=self.value())


class SubmissionResultFilter(admin.SimpleListFilter):
    parameter_name = title = 'result'
    __lookups = (('None', 'None'),) + Submission.RESULT
    __handles = set(map(itemgetter(0), Submission.RESULT))

    def lookups(self, request, model_admin):
        return self.__lookups

    def queryset(self, request, queryset):
        if self.value() == 'None':
            return queryset.filter(result=None)
        if self.value() in self.__handles:
            return queryset.filter(result=self.value())


class SubmissionAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'problem', 'date')
    fields = ('user', 'problem', 'date', 'time', 'memory', 'points', 'language', 'source', 'status', 'result')
    actions = ['judge']
    list_display = ('id', 'problem_code', 'problem_name', 'user', 'execution_time', 'pretty_memory',
                    'points', 'language', 'status', 'result', 'judge_column')
    list_filter = ('language', SubmissionStatusFilter, SubmissionResultFilter)
    search_fields = ('problem__code', 'problem__name', 'user__user__username', 'user__name')

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
    search_fields = ['author__user__username', 'author__name', 'page', 'title', 'body']

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
    fields = ('key', 'name', 'short_name', 'common_name', 'ace', 'pygments', 'info', 'description', 'problems')
    form = LanguageForm

    if AdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': AdminPagedownWidget},
        }

    def save_model(self, request, obj, form, change):
        super(LanguageAdmin, self).save_model(request, obj, form, change)
        obj.problem_set = form.cleaned_data['problems']
        obj.save()

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
        obj.problem_set = form.cleaned_data['problems']
        obj.save()

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


class NavigationBarAdmin(admin.ModelAdmin):
    list_display = ('key', 'label', 'path', 'order', 'order_link')
    fields = ('key', 'label', 'path', 'regex')


class JudgeAdminForm(ModelForm):
    class Meta:
        model = Judge
        widgets = {
            'auth_key': GenerateKeyTextInput(),
        }


class JudgeAdmin(admin.ModelAdmin):
    form = JudgeAdminForm
    readonly_fields = ('created', 'online', 'last_connect', 'ping', 'load', 'runtimes', 'problems')
    fieldsets = (
        (None, {'fields': ('name', 'auth_key')}),
        ('Information', {'fields': ('created', 'online', 'last_connect', 'ping', 'load')}),
        ('Capabilities', {'fields': ('runtimes', 'problems')}),
    )
    list_display = ('name', 'online', 'last_connect', 'ping', 'load')
    ordering = ['name']


class ContestProblemInline(admin.TabularInline):
    model = ContestProblem
    fields = ('problem', 'points', 'partial')


class ContestAdmin(admin.ModelAdmin):
    fields = ('key', 'name', 'description', 'ongoing', 'is_public', 'time_limit')
    list_display = ('key', 'name', 'ongoing', 'is_public', 'time_limit')
    actions = ['make_public', 'make_private']
    inlines = [ContestProblemInline]

    if AdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': AdminPagedownWidget},
        }

    def make_public(self, request, queryset):
        count = queryset.update(is_public=True)
        self.message_user(request, "%d contest%s successfully marked as public." % (count, 's'[count == 1:]))
    make_public.short_description = 'Mark contests as public'

    def make_private(self, request, queryset):
        count = queryset.update(is_public=False)
        self.message_user(request, "%d contest%s successfully marked as private." % (count, 's'[count == 1:]))
    make_private.short_description = 'Mark contests as private'


class ContestParticipationAdmin(admin.ModelAdmin):
    """For developer use only."""
    fields = ('contest', 'profile', 'start')
    list_display = ('contest', 'username', 'start')

    @staticmethod
    def username(obj):
        return obj.profile.user.display_name

admin.site.register(Language, LanguageAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Problem, ProblemAdmin)
admin.site.register(ProblemGroup, ProblemGroupAdmin)
admin.site.register(ProblemType, ProblemGroupAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(MiscConfig)
admin.site.register(NavigationBar, NavigationBarAdmin)
admin.site.register(Judge, JudgeAdmin)
admin.site.register(Contest, ContestAdmin)
admin.site.register(ContestParticipation, ContestParticipationAdmin)
