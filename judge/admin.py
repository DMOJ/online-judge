from operator import itemgetter, attrgetter
from django.conf import settings

from django.contrib import admin, messages
from django.conf.urls import patterns, url
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.flatpages.admin import FlatPageAdmin
from django.core.cache import cache
from django.db.models import TextField, Q
from django.forms import ModelForm, ModelMultipleChoiceField, TextInput
from django.http import HttpResponseRedirect, Http404
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from judge.models import Language, Profile, Problem, ProblemGroup, ProblemType, Submission, Comment, \
    MiscConfig, Judge, NavigationBar, Contest, ContestParticipation, ContestProblem, Organization, BlogPost, \
    ContestProfile, SubmissionTestCase, Solution
from judge.widgets import CheckboxSelectMultipleWithSelectAll, AdminPagedownWidget, MathJaxAdminPagedownWidget

try:
    from django_select2.widgets import HeavySelect2MultipleWidget
except ImportError:
    HeavySelect2MultipleWidget = None

use_select2 = HeavySelect2MultipleWidget is not None and 'django_select2' in settings.INSTALLED_APPS


class ContestProfileInlineForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ContestProfileInlineForm, self).__init__(*args, **kwargs)
        self.fields['current'].queryset = self.instance.history.select_related('contest').all()
        self.fields['current'].label_from_instance = lambda obj: obj.contest.name


class ContestProfileInline(admin.StackedInline):
    fields = ('current',)
    model = ContestProfile
    form = ContestProfileInlineForm
    can_delete = False


class ProfileAdmin(admin.ModelAdmin):
    fields = ('user', 'name', 'display_rank', 'about', 'organization', 'timezone', 'language', 'ace_theme',
              'last_access', 'ip')
    list_display = ('admin_user_admin', 'email', 'timezone_full', 'language', 'last_access', 'ip')
    ordering = ('user__username',)
    search_fields = ('user__username', 'name', 'ip', 'user__email')
    list_filter = ('language', 'timezone')
    actions = ('recalculate_points',)
    inlines = [ContestProfileInline]
    actions_on_top = True
    actions_on_bottom = True

    def admin_user_admin(self, obj):
        return obj.long_display_name
    admin_user_admin.admin_order_field = 'user__username'
    admin_user_admin.short_description = 'User'

    def email(self, obj):
        return obj.user.email
    email.admin_order_field = 'user__email'
    email.short_description = 'Email'

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


class ProblemForm(ModelForm):
    class Meta:
        model = Problem
        if use_select2:
            widgets = {
                'authors': HeavySelect2MultipleWidget(data_view='profile_select2'),
                'banned_users': HeavySelect2MultipleWidget(data_view='profile_select2'),
            }


class ProblemAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'is_public', 'date', 'authors', 'description')
        }),
        ('Taxonomy', {'fields': ('types', 'group')}),
        ('Points', {'fields': (('points', 'partial'), 'short_circuit')}),
        ('Limits', {'fields': ('time_limit', 'memory_limit')}),
        ('Language', {'fields': ('allowed_languages',)}),
        ('Justice', {'fields': ('banned_users',)})
    )
    list_display = ['code', 'name', 'show_authors', 'points', 'is_public']
    ordering = ['code']
    search_fields = ('code', 'name')
    actions = ['make_public', 'make_private']
    list_per_page = 500
    list_max_show_all = 1000
    actions_on_top = True
    actions_on_bottom = True
    form = ProblemForm

    if not use_select2:
        filter_horizontal = ['authors', 'banned_users']

    if MathJaxAdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': MathJaxAdminPagedownWidget},
        }

    def show_authors(self, obj):
        return ', '.join(map(attrgetter('user.username'), obj.authors.select_related('user')))
    show_authors.short_description = 'Authors'

    def make_public(self, request, queryset):
        count = queryset.update(is_public=True)
        self.message_user(request, "%d problem%s successfully marked as public." % (count, 's'[count == 1:]))

    make_public.short_description = 'Mark problems as public'

    def make_private(self, request, queryset):
        count = queryset.update(is_public=False)
        self.message_user(request, "%d problem%s successfully marked as private." % (count, 's'[count == 1:]))

    make_private.short_description = 'Mark problems as private'

    def get_queryset(self, request):
        if request.user.has_perm('judge.edit_all_problem'):
            return Problem.objects.all()
        else:
            return Problem.objects.filter(authors__id=request.user.profile.id)

    def has_change_permission(self, request, obj=None):
        if not request.user.has_perm('judge.edit_own_problem'):
            return False
        if request.user.has_perm('judge.edit_all_problem') or obj is None:
            return True
        return obj.authors.filter(id=request.user.profile.id).exists()

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'allowed_languages':
            kwargs['widget'] = CheckboxSelectMultipleWithSelectAll()
        return super(ProblemAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def get_form(self, *args, **kwargs):
        form = super(ProblemAdmin, self).get_form(*args, **kwargs)
        form.base_fields['authors'].queryset = Profile.objects.all()
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
    __lookups = (('None', 'None'), ('BAD', 'Unaccepted')) + Submission.RESULT
    __handles = set(map(itemgetter(0), Submission.RESULT))

    def lookups(self, request, model_admin):
        return self.__lookups

    def queryset(self, request, queryset):
        if self.value() == 'None':
            return queryset.filter(result=None)
        elif self.value() == 'BAD':
            return queryset.exclude(result='AC')
        elif self.value() in self.__handles:
            return queryset.filter(result=self.value())


class SubmissionTestCaseAdmin(admin.TabularInline):
    fields = ('case', 'batch', 'status', 'time', 'memory', 'points', 'total')
    readonly_fields = ('case', 'batch', 'total')
    model = SubmissionTestCase
    can_delete = False
    max_num = 0


class SubmissionAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'problem', 'date')
    fields = ('user', 'problem', 'date', 'time', 'memory', 'points', 'language', 'source', 'status', 'result')
    actions = ('judge', 'recalculate_score')
    list_display = ('id', 'problem_code', 'problem_name', 'user_column', 'execution_time', 'pretty_memory',
                    'points', 'language', 'status', 'result', 'judge_column')
    list_filter = ('language', SubmissionStatusFilter, SubmissionResultFilter)
    search_fields = ('problem__code', 'problem__name', 'user__user__username', 'user__name')
    actions_on_top = True
    actions_on_bottom = True
    inlines = [SubmissionTestCaseAdmin]

    def user_column(self, obj):
        return format_html(u'<span title="{display}">{username}</span>',
                           username=obj.user.user.username,
                           display=obj.user.name)
    user_column.admin_order_field = 'user__user__username'
    user_column.short_description = 'User'

    def get_queryset(self, request):
        if request.user.has_perm('judge.edit_all_problem'):
            return Submission.objects.all()
        else:
            return Submission.objects.filter(problem__authors__id=request.user.profile.id)

    def has_change_permission(self, request, obj=None):
        if not request.user.has_perm('judge.edit_own_problem'):
            return False
        if request.user.has_perm('judge.edit_all_problem') or obj is None:
            return True
        return obj.problem.authors.filter(id=request.user.profile.id).exists()

    def judge(self, request, queryset):
        if not request.user.has_perm('judge.rejudge_submission') or not request.user.has_perm('judge.edit_own_problem'):
            self.message_user(request, 'You do not have the permission to rejudge submissions.', level=messages.ERROR)
            return
        successful = 0
        queryset = queryset.order_by('id')
        if queryset.count() > 10 and not request.user.has_perm('judge.rejudge_submission_lot'):
            self.message_user(request, 'You do not have the permission to rejudge THAT many submissions.',
                              level=messages.ERROR)
            return
        if not request.user.has_perm('judge.edit_all_problem'):
            queryset = queryset.filter(problem__authors__id=request.user.profile.id)
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

    def recalculate_score(self, request, queryset):
        if not request.user.has_perm('judge.rejudge_submission'):
            self.message_user(request, 'You do not have the permission to rejudge submissions.', level=messages.ERROR)
            return
        submissions = list(queryset.select_related('problem').only('points', 'case_points', 'case_total',
                                                                   'problem__partial', 'problem__points'))
        for submission in submissions:
            submission.points = round(submission.case_points / submission.case_total * submission.problem.points
                                      if submission.case_total else 0, 1)
            if not submission.problem.partial and submission.points < submission.problem.points:
                submission.points = 0
            submission.save()

        for profile in Profile.objects.filter(id__in=queryset.values_list('user_id', flat=True).distinct()):
            profile.calculate_points()
            cache.delete('user_complete:%d' % profile.id)

        self.message_user(request, '%d submission%s were successfully rescored.' %
                          (len(submissions), 's'[len(submissions) == 1:]))
    recalculate_score.short_description = 'Rescore the selected submissions'

    def problem_code(self, obj):
        return obj.problem.code
    problem_code.admin_order_field = 'problem__code'

    def problem_name(self, obj):
        return obj.problem.name
    problem_name.admin_order_field = 'problem__name'

    def get_urls(self):
        urls = super(SubmissionAdmin, self).get_urls()
        my_urls = patterns('',
                           url(r'^(\d+)/judge/$', self.judge_view, name='judge_submission_rejudge'),
        )
        return my_urls + urls

    def judge_view(self, request, id):
        if not request.user.has_perm('judge.rejudge_submission') or not request.user.has_perm('judge.edit_own_problem'):
            raise PermissionDenied()
        try:
            submission = Submission.objects.get(id=id)
        except ObjectDoesNotExist:
            raise Http404()
        if not request.user.has_perm('judge.edit_all_problem') and \
                not submission.problem.authors.filter(id=request.user.profile.id).exists():
            raise PermissionDenied()
        submission.judge()
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
    list_display = ['title', 'author', 'linked_page', 'time']
    search_fields = ['author__user__username', 'author__name', 'page', 'title', 'body']
    actions_on_top = True
    actions_on_bottom = True

    def linked_page(self, obj):
        link = obj.link
        
        if link is not None:
            return format_html('<a href="{0}">{1}</a>', link, obj.page)
        else:
            return format_html('{0}', obj.page)
    linked_page.short_description = 'Associated page'
    linked_page.allow_tags = True
    linked_page.admin_order_field = 'page'

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
    list_display = ('key', 'label', 'path', 'order', 'order_link', 'parent_name')
    fields = ('key', 'label', 'path', 'regex', 'parent')

    def parent_name(self, obj):
        return obj.parent and obj.parent.label
    parent_name.short_description = 'Parent'


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
        ('Description', {'fields': ('description',)}),
        ('Information', {'fields': ('created', 'online', 'last_connect', 'ping', 'load')}),
        ('Capabilities', {'fields': ('runtimes', 'problems')}),
    )
    list_display = ('name', 'online', 'last_connect', 'ping', 'load')
    ordering = ['name']

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.online:
            return self.readonly_fields + ('name',)
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        result = super(JudgeAdmin, self).has_delete_permission(request, obj)
        if result and obj is not None:
            return not obj.online
        return result

    if AdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': AdminPagedownWidget},
        }


class ContestProblemInline(admin.TabularInline):
    model = ContestProblem
    fields = ('problem', 'points', 'partial')


class ContestAdmin(admin.ModelAdmin):
    fields = ('key', 'name', 'organizers', 'description', 'ongoing', 'free_start', 'is_public', 'is_external', 'start_time', 'time_limit')
    list_display = ('key', 'name', 'ongoing', 'is_public', 'is_external', 'time_limit')
    actions = ['make_public', 'make_private']
    inlines = [ContestProblemInline]
    actions_on_top = True
    actions_on_bottom = True
    filter_horizontal = ['organizers']

    if MathJaxAdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': MathJaxAdminPagedownWidget},
        }

    def make_public(self, request, queryset):
        count = queryset.update(is_public=True)
        self.message_user(request, "%d contest%s successfully marked as public." % (count, 's'[count == 1:]))
    make_public.short_description = 'Mark contests as public'

    def make_private(self, request, queryset):
        count = queryset.update(is_public=False)
        self.message_user(request, "%d contest%s successfully marked as private." % (count, 's'[count == 1:]))
    make_private.short_description = 'Mark contests as private'

    def get_queryset(self, request):
        if request.user.has_perm('judge.edit_all_contest'):
            return Contest.objects.all()
        else:
            return Contest.objects.filter(organizers__id=request.user.profile.id)

    def has_change_permission(self, request, obj=None):
        if not request.user.has_perm('judge.edit_own_contest'):
            return False
        if request.user.has_perm('judge.edit_all_contest') or obj is None:
            return True
        return obj.organizers.filter(id=request.user.profile.id).exists()

    def get_form(self, *args, **kwargs):
        form = super(ContestAdmin, self).get_form(*args, **kwargs)
        perms = ('edit_own_contest', 'edit_all_contest')
        form.base_fields['organizers'].queryset = Profile.objects.filter(
            Q(user__is_superuser=True) |
            Q(user__groups__permissions__codename__in=perms) |
            Q(user__user_permissions__codename__in=perms)
        ).distinct()
        return form


class ContestParticipationAdmin(admin.ModelAdmin):
    fields = ('contest', 'profile', 'real_start')
    list_display = ('contest', 'username', 'real_start')
    actions = ['recalculate_points', 'recalculate_cumtime']
    actions_on_bottom = actions_on_top = True
    search_fields = ('contest__key', 'contest__name', 'profile__user__user__username', 'profile__user__name')

    def username(self, obj):
        return obj.profile.user.long_display_name
    username.admin_order_field = 'profile__user__user__username'

    def recalculate_points(self, request, queryset):
        count = 0
        for participation in queryset:
            participation.recalculate_score()
            count += 1
        self.message_user(request, "%d participation%s have scores recalculated." % (count, 's'[count == 1:]))
    recalculate_points.short_description = 'Recalculate scores'

    def recalculate_cumtime(self, request, queryset):
        count = 0
        for participation in queryset:
            participation.update_cumtime()
            count += 1
        self.message_user(request, "%d participation%s have times recalculated." % (count, 's'[count == 1:]))
    recalculate_cumtime.short_description = 'Recalculate cumulative time'


class OrganizationAdmin(admin.ModelAdmin):
    readonly_fields = ('creation_date',)
    fields = ('name', 'key', 'short_name', 'about', 'registrant', 'creation_date', 'admins')
    list_display = ('name', 'key', 'short_name', 'registrant', 'creation_date')
    actions_on_top = True
    actions_on_bottom = True
    filter_horizontal = ('admins',)

    if MathJaxAdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': MathJaxAdminPagedownWidget},
        }


class BlogPostAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'visible', 'sticky', 'publish_on')}),
        ('Content', {'fields': ('content',)}),
        ('Summary', {'classes': ('collapse',), 'fields': ('summary',)}),
    )
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('id', 'title', 'visible', 'sticky', 'publish_on')
    list_display_links = ('id', 'title')
    ordering = ('-publish_on',)

    if AdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': AdminPagedownWidget},
        }


class SolutionAdmin(FlatPageAdmin):
    fieldsets = (
        (None, {'fields': ('url', 'title', 'content', 'sites')}),
        ('Advanced options', {'classes': ('collapse',), 'fields': ('enable_comments', 'registration_required')}),
    )

    def get_queryset(self, request):
        return Solution.objects.filter(url__startswith='/solution/')

    if MathJaxAdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': MathJaxAdminPagedownWidget},
        }

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
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(BlogPost, BlogPostAdmin)
admin.site.register(Solution, SolutionAdmin)
