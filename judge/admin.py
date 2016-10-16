from functools import partial
from operator import itemgetter, attrgetter

from django import forms
from django.conf.urls import url
from django.contrib import admin, messages
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import transaction, connection
from django.db.models import TextField, Q
from django.forms import ModelForm, ModelMultipleChoiceField, TextInput
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext, ungettext, pgettext
from mptt.admin import MPTTModelAdmin
from reversion.admin import VersionAdmin

from judge.dblock import LockModel
from judge.models import Language, Profile, Problem, ProblemGroup, ProblemType, Submission, Comment, \
    MiscConfig, Judge, NavigationBar, Contest, ContestParticipation, ContestProblem, Organization, BlogPost, \
    SubmissionTestCase, Solution, Rating, ContestSubmission, License, LanguageLimit, OrganizationRequest, \
    ContestTag, ProblemTranslation
from judge.ratings import rate_contest
from judge.widgets import AdminPagedownWidget, MathJaxAdminPagedownWidget, \
    HeavyPreviewAdminPageDownWidget, CheckboxSelectMultipleWithSelectAll, \
    HeavySelect2Widget, HeavySelect2MultipleWidget, Select2Widget, Select2MultipleWidget


class HeavySelect2Widget(HeavySelect2Widget):
    @property
    def is_hidden(self):
        return False


# try:
#    from suit.admin import SortableModelAdmin, SortableTabularInline
# except ImportError:
SortableModelAdmin = object
SortableTabularInline = admin.TabularInline


class ProfileForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['current_contest'].queryset = self.instance.contest_history.select_related('contest') \
            .only('contest__name', 'user_id', 'virtual')
        self.fields['current_contest'].label_from_instance = (lambda obj: '%s v%d' % (obj.contest.name, obj.virtual)
        if obj.virtual else obj.contest.name)

    class Meta:
        widgets = {
            'timezone': Select2Widget,
            'language': Select2Widget,
            'ace_theme': Select2Widget,
            'current_contest': Select2Widget,
        }
        if AdminPagedownWidget is not None:
            widgets['about'] = AdminPagedownWidget


class TimezoneFilter(admin.SimpleListFilter):
    title = _('Location')
    parameter_name = 'timezone'

    def lookups(self, request, model_admin):
        return Profile.objects.values_list('timezone', 'timezone').distinct().order_by('timezone')

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(timezone=self.value())


class ProfileAdmin(VersionAdmin):
    fields = ('user', 'name', 'display_rank', 'about', 'organizations', 'timezone', 'language', 'ace_theme',
              'math_engine', 'last_access', 'ip', 'mute', 'user_script', 'current_contest')
    readonly_fields = ('user',)
    list_display = ('admin_user_admin', 'email', 'timezone_full', 'date_joined', 'last_access', 'ip', 'show_public')
    ordering = ('user__username',)
    search_fields = ('user__username', 'name', 'ip', 'user__email')
    list_filter = ('language', TimezoneFilter)
    actions = ('recalculate_points',)
    actions_on_top = True
    actions_on_bottom = True
    form = ProfileForm

    def show_public(self, obj):
        format = '<a href="{0}" style="white-space:nowrap;">%s</a>' % ugettext('View on site')
        return format_html(format, obj.get_absolute_url())

    show_public.short_description = ''

    def admin_user_admin(self, obj):
        return obj.long_display_name

    admin_user_admin.admin_order_field = 'user__username'
    admin_user_admin.short_description = _('User')

    def email(self, obj):
        return obj.user.email

    email.admin_order_field = 'user__email'
    email.short_description = _('Email')

    def timezone_full(self, obj):
        return obj.timezone

    timezone_full.admin_order_field = 'timezone'
    timezone_full.short_description = _('Timezone')

    def date_joined(self, obj):
        return obj.user.date_joined

    date_joined.admin_order_field = 'user__date_joined'
    date_joined.short_description = _('date joined')

    def recalculate_points(self, request, queryset):
        count = 0
        for profile in queryset:
            profile.calculate_points()
            count += 1
        self.message_user(request, ungettext('%d user have scores recalculated.',
                                             '%d users have scores recalculated.',
                                             count) % count)

    recalculate_points.short_description = _('Recalculate scores')


class ProblemForm(ModelForm):
    change_message = forms.CharField(max_length=256, label='Edit reason', required=False)

    def __init__(self, *args, **kwargs):
        super(ProblemForm, self).__init__(*args, **kwargs)
        self.fields['authors'].widget.can_add_related = False
        self.fields['testers'].widget.can_add_related = False
        self.fields['banned_users'].widget.can_add_related = False
        self.fields['change_message'].widget.attrs.update({
            'placeholder': ugettext('Describe the changes you made (optional)')
        })

    class Meta:
        widgets = {
            'authors': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
            'testers': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
            'banned_users': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
            'types': Select2MultipleWidget,
            'group': Select2Widget,
        }
        if HeavyPreviewAdminPageDownWidget is not None:
            widgets['description'] = HeavyPreviewAdminPageDownWidget(preview=reverse_lazy('problem_preview'))


class BlogPostForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(BlogPostForm, self).__init__(*args, **kwargs)
        self.fields['authors'].widget.can_add_related = False

    class Meta:
        widgets = {
            'authors': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
        }


class ProblemCreatorListFilter(admin.SimpleListFilter):
    title = parameter_name = 'creator'

    def lookups(self, request, model_admin):
        return [(name, name) for name in Profile.objects.exclude(authored_problems=None)
            .values_list('user__username', flat=True)]

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(authors__user__username=self.value())


class LanguageLimitInlineForm(ModelForm):
    class Meta:
        widgets = {
            'language': Select2Widget,
        }


class LanguageLimitInline(admin.TabularInline):
    model = LanguageLimit
    fields = ('language', 'time_limit', 'memory_limit')
    form = LanguageLimitInlineForm


class ProblemTranslationForm(ModelForm):
    class Meta:
        if HeavyPreviewAdminPageDownWidget is not None:
            widgets = {'description': HeavyPreviewAdminPageDownWidget(preview=reverse_lazy('problem_preview'))}


class ProblemTranslationInline(admin.StackedInline):
    model = ProblemTranslation
    fields = ('language', 'name', 'description')
    form = ProblemTranslationForm
    extra = 0


class ProblemAdmin(VersionAdmin):
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'is_public', 'date', 'authors', 'testers', 'description', 'license')
        }),
        (_('Taxonomy'), {'fields': ('types', 'group')}),
        (_('Points'), {'fields': (('points', 'partial'), 'short_circuit')}),
        (_('Limits'), {'fields': ('time_limit', 'memory_limit')}),
        (_('Language'), {'fields': ('allowed_languages',)}),
        (_('Justice'), {'fields': ('banned_users',)}),
        (_('History'), {'fields': ('change_message',)})
    )
    list_display = ['code', 'name', 'show_authors', 'points', 'is_public', 'show_public']
    ordering = ['code']
    search_fields = ('code', 'name')
    inlines = [LanguageLimitInline, ProblemTranslationInline]
    list_max_show_all = 1000
    actions_on_top = True
    actions_on_bottom = True
    list_filter = ('is_public', ProblemCreatorListFilter)
    form = ProblemForm

    def get_actions(self, request):
        actions = super(ProblemAdmin, self).get_actions(request)

        if request.user.has_perm('judge.change_public_visibility'):
            func, name, desc = self.get_action('make_public')
            actions[name] = (func, name, desc)

            func, name, desc = self.get_action('make_private')
            actions[name] = (func, name, desc)

        return actions

    def get_readonly_fields(self, request, obj=None):
        if not request.user.has_perm('judge.change_public_visibility'):
            return self.readonly_fields + ('is_public',)
        return self.readonly_fields

    def show_authors(self, obj):
        return ', '.join(map(attrgetter('user.username'), obj.authors.all()))

    show_authors.short_description = _('Authors')

    def show_public(self, obj):
        return format_html(u'<a href="{1}">{0}</a>', ugettext('View on site'), obj.get_absolute_url())

    show_public.short_description = ''

    def _update_points(self, problem_id, sign):
        with connection.cursor() as c:
            c.execute('''
                UPDATE judge_profile prof INNER JOIN (
                    SELECT sub.user_id AS user_id, MAX(sub.points) AS delta
                    FROM judge_submission sub
                    WHERE sub.problem_id = %s
                    GROUP BY sub.user_id
                ) `data` ON (`data`.user_id = prof.id)
                SET prof.points = prof.points {} `data`.delta
                WHERE `data`.delta IS NOT NULL
            '''.format(sign), (problem_id,))

    def _update_points_many(self, ids, sign):
        with connection.cursor() as c:
            c.execute('''
                UPDATE judge_profile prof INNER JOIN (
                    SELECT deltas.id, SUM(deltas) AS delta FROM (
                        SELECT sub.user_id AS id, MAX(sub.points) AS deltas
                             FROM judge_submission sub
                             WHERE sub.problem_id IN ({})
                             GROUP BY sub.user_id, sub.problem_id
                    ) deltas GROUP BY id
                ) `data` ON (`data`.id = prof.id)
                SET prof.points = prof.points {} `data`.delta
                WHERE `data`.delta IS NOT NULL
            '''.format(', '.join(['%s'] * len(ids)), sign), ids)

    def make_public(self, request, queryset):
        count = queryset.update(is_public=True)
        self._update_points_many(queryset.values_list('id', flat=True), '+')
        self.message_user(request, ungettext('%d problem successfully marked as public.',
                                             '%d problems successfully marked as public.',
                                             count) % count)

    make_public.short_description = _('Mark problems as public')

    def make_private(self, request, queryset):
        count = queryset.update(is_public=False)
        self._update_points_many(queryset.values_list('id', flat=True), '-')
        self.message_user(request, ungettext('%d problem successfully marked as private.',
                                             '%d problems successfully marked as private.',
                                             count) % count)

    make_private.short_description = _('Mark problems as private')

    def get_queryset(self, request):
        queryset = Problem.objects.prefetch_related('authors__user')
        if request.user.has_perm('judge.edit_all_problem'):
            return queryset

        access = Q()
        if request.user.has_perm('judge.edit_public_problem'):
            access |= Q(is_public=True)
        if request.user.has_perm('judge.edit_own_problem'):
            access |= Q(authors__id=request.user.profile.id)
        return queryset.filter(access).distinct() if access else queryset.none()

    def has_change_permission(self, request, obj=None):
        if request.user.has_perm('judge.edit_all_problem') or obj is None:
            return True
        if request.user.has_perm('judge.edit_public_problem') and obj.is_public:
            return True
        if not request.user.has_perm('judge.edit_own_problem'):
            return False
        return obj.authors.filter(id=request.user.profile.id).exists()

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'allowed_languages':
            kwargs['widget'] = CheckboxSelectMultipleWithSelectAll()
        return super(ProblemAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def get_form(self, *args, **kwargs):
        form = super(ProblemAdmin, self).get_form(*args, **kwargs)
        form.base_fields['authors'].queryset = Profile.objects.all()
        return form

    def save_model(self, request, obj, form, change):
        super(ProblemAdmin, self).save_model(request, obj, form, change)
        if form.changed_data and 'is_public' in form.changed_data:
            self._update_points(obj.id, '+' if obj.is_public else '-')

    def construct_change_message(self, request, form, *args, **kwargs):
        if form.cleaned_data.get('change_message'):
            return form.cleaned_data['change_message']
        return super(ProblemAdmin, self).construct_change_message(request, form, *args, **kwargs)


class SubmissionStatusFilter(admin.SimpleListFilter):
    parameter_name = title = 'status'
    __lookups = (('None', _('None')), ('NotDone', _('Not done')), ('EX', _('Exceptional'))) + Submission.STATUS
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
    __lookups = (('None', _('None')), ('BAD', _('Unaccepted'))) + Submission.RESULT
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


class SubmissionTestCaseInline(admin.TabularInline):
    fields = ('case', 'batch', 'status', 'time', 'memory', 'points', 'total')
    readonly_fields = ('case', 'batch', 'total')
    model = SubmissionTestCase
    can_delete = False
    max_num = 0


class ContestSubmissionInline(admin.StackedInline):
    fields = ('problem', 'participation', 'points')
    model = ContestSubmission

    def get_formset(self, request, obj=None, **kwargs):
        kwargs['formfield_callback'] = partial(self.formfield_for_dbfield, request=request, obj=obj)
        return super(ContestSubmissionInline, self).get_formset(request, obj, **kwargs)

    def formfield_for_dbfield(self, db_field, **kwargs):
        submission = kwargs.pop('obj', None)
        label = None
        if submission:
            if db_field.name == 'participation':
                kwargs['queryset'] = ContestParticipation.objects.filter(user=submission.user,
                                                                         contest__problems=submission.problem) \
                    .only('id', 'contest__name')
                label = lambda obj: obj.contest.name
            elif db_field.name == 'problem':
                kwargs['queryset'] = ContestProblem.objects.filter(problem=submission.problem) \
                    .only('id', 'problem__name', 'contest__name')
                label = lambda obj: pgettext('contest problem', '%(problem)s in %(contest)s') % {
                    'problem': obj.problem.name, 'contest': obj.contest.name
                }
        field = super(ContestSubmissionInline, self).formfield_for_dbfield(db_field, **kwargs)
        if label is not None:
            field.label_from_instance = label
        return field


class SubmissionAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'problem', 'date')
    fields = ('user', 'problem', 'date', 'time', 'memory', 'points', 'language', 'source', 'status', 'result',
              'case_points', 'case_total', 'judged_on', 'error')
    actions = ('judge', 'recalculate_score')
    list_display = ('id', 'problem_code', 'problem_name', 'user_column', 'execution_time', 'pretty_memory',
                    'points', 'language', 'status', 'result', 'judge_column')
    list_filter = ('language', SubmissionStatusFilter, SubmissionResultFilter)
    search_fields = ('problem__code', 'problem__name', 'user__user__username', 'user__name')
    actions_on_top = True
    actions_on_bottom = True
    inlines = [SubmissionTestCaseInline, ContestSubmissionInline]

    def user_column(self, obj):
        return format_html(u'<span title="{display}">{username}</span>',
                           username=obj.user.user.username,
                           display=obj.user.name)

    user_column.admin_order_field = 'user__user__username'
    user_column.short_description = _('User')

    def get_queryset(self, request):
        queryset = Submission.objects.only(
            'problem__code', 'problem__name', 'user__user__username', 'user__name', 'language__name',
            'time', 'memory', 'points', 'status', 'result'
        )
        if not request.user.has_perm('judge.edit_all_problem'):
            queryset = queryset.filter(problem__authors__id=request.user.profile.id)
        return queryset

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if not request.user.has_perm('judge.edit_own_problem'):
            return False
        if request.user.has_perm('judge.edit_all_problem') or obj is None:
            return True
        return obj.problem.authors.filter(id=request.user.profile.id).exists()

    def judge(self, request, queryset):
        if not request.user.has_perm('judge.rejudge_submission') or not request.user.has_perm('judge.edit_own_problem'):
            self.message_user(request, ugettext('You do not have the permission to rejudge submissions.'),
                              level=messages.ERROR)
            return
        queryset = queryset.order_by('id')
        if queryset.count() > 10 and not request.user.has_perm('judge.rejudge_submission_lot'):
            self.message_user(request, ugettext('You do not have the permission to rejudge THAT many submissions.'),
                              level=messages.ERROR)
            return
        if not request.user.has_perm('judge.edit_all_problem'):
            queryset = queryset.filter(problem__authors__id=request.user.profile.id)
        judged = len(queryset)
        for model in queryset:
            model.was_rejudged = True
            model.judge()
        self.message_user(request, ungettext('%d submission were successfully scheduled for rejudging.',
                                             '%d submissions were successfully scheduled for rejudging.',
                                             judged) % judged)

    judge.short_description = _('Rejudge the selected submissions')

    def execution_time(self, obj):
        return round(obj.time, 2) if obj.time is not None else 'None'

    execution_time.admin_order_field = 'time'

    def pretty_memory(self, obj):
        memory = obj.memory
        if memory is None:
            return ugettext('None')
        if memory < 1000:
            return ugettext('%d KB') % memory
        else:
            return ugettext('%.2f MB') % (memory / 1024.)

    pretty_memory.admin_order_field = 'memory'
    pretty_memory.short_description = _('Memory Usage')

    def recalculate_score(self, request, queryset):
        if not request.user.has_perm('judge.rejudge_submission'):
            self.message_user(request, ugettext('You do not have the permission to rejudge submissions.'),
                              level=messages.ERROR)
            return
        submissions = list(queryset.select_related('problem').only('points', 'case_points', 'case_total',
                                                                   'problem__partial', 'problem__points'))
        for submission in submissions:
            submission.points = round(submission.case_points / submission.case_total * submission.problem.points
                                      if submission.case_total else 0, 1)
            if not submission.problem.partial and submission.points < submission.problem.points:
                submission.points = 0
            submission.save()

            if hasattr(submission, 'contest'):
                contest = submission.contest
                contest.points = round(submission.case_points / submission.case_total * contest.problem.points
                                       if submission.case_total > 0 else 0, 1)
                if not contest.problem.partial and contest.points < contest.problem.points:
                    contest.points = 0
                contest.save()

        for profile in Profile.objects.filter(id__in=queryset.values_list('user_id', flat=True).distinct()):
            profile.calculate_points()
            cache.delete('user_complete:%d' % profile.id)
            cache.delete('user_attempted:%d' % profile.id)

        for participation in ContestParticipation.objects.filter(
                id__in=queryset.values_list('contest__participation_id')):
            participation.recalculate_score()

        self.message_user(request, ungettext('%d submission were successfully rescored.',
                                             '%d submissions were successfully rescored.',
                                             len(submissions)) % len(submissions))

    recalculate_score.short_description = _('Rescore the selected submissions')

    def problem_code(self, obj):
        return obj.problem.code

    problem_code.admin_order_field = 'problem__code'

    def problem_name(self, obj):
        return obj.problem.name

    problem_name.admin_order_field = 'problem__name'

    def get_urls(self):
        return [url(r'^(\d+)/judge/$', self.judge_view, name='judge_submission_rejudge')] + \
               super(SubmissionAdmin, self).get_urls()

    def judge_view(self, request, id):
        if not request.user.has_perm('judge.rejudge_submission') or not request.user.has_perm('judge.edit_own_problem'):
            raise PermissionDenied()
        submission = get_object_or_404(Submission, id=id)
        if not request.user.has_perm('judge.edit_all_problem') and \
                not submission.problem.authors.filter(id=request.user.profile.id).exists():
            raise PermissionDenied()
        submission.judge()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    def judge_column(self, obj):
        return '<input type="button" value="Rejudge" onclick="location.href=\'%s/judge/\'" />' % obj.id

    judge_column.short_description = ''
    judge_column.allow_tags = True


class CommentForm(ModelForm):
    class Meta:
        widgets = {
            'author': HeavySelect2Widget(data_view='profile_select2'),
            'parent': HeavySelect2Widget(data_view='comment_select2'),
        }


class CommentAdmin(VersionAdmin):
    fieldsets = (
        (None, {'fields': ('author', 'page', 'parent', 'score', 'hidden')}),
        ('Content', {'fields': ('title', 'body')}),
    )
    list_display = ['title', 'author', 'linked_page', 'time']
    search_fields = ['author__user__username', 'author__name', 'page', 'title', 'body']
    actions = ['hide_comment', 'unhide_comment']
    list_filter = ['hidden']
    actions_on_top = True
    actions_on_bottom = True
    form = CommentForm

    def hide_comment(self, request, queryset):
        count = queryset.update(hidden=True)
        self.message_user(request, ungettext('%d comment successfully hidden.',
                                             '%d comments successfully hidden.',
                                             count) % count)

    hide_comment.short_description = _('Hide comments')

    def unhide_comment(self, request, queryset):
        count = queryset.update(hidden=False)
        self.message_user(request, ungettext('%d comment successfully unhidden.',
                                             '%d comments successfully unhidden.',
                                             count) % count)

    unhide_comment.short_description = _('Unhide comments')

    def get_queryset(self, request):
        return Comment.objects.order_by('-time')

    def linked_page(self, obj):
        link = obj.link

        if link is not None:
            return format_html('<a href="{0}">{1}</a>', link, obj.page)
        else:
            return format_html('{0}', obj.page)

    linked_page.short_description = _('Associated page')
    linked_page.allow_tags = True
    linked_page.admin_order_field = 'page'

    if MathJaxAdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': MathJaxAdminPagedownWidget},
        }


class LanguageForm(ModelForm):
    problems = ModelMultipleChoiceField(
        label=_('Disallowed problems'),
        queryset=Problem.objects.all(),
        required=False,
        help_text=_('These problems are NOT allowed to be submitted in this language'),
        widget=HeavySelect2MultipleWidget(data_view='problem_select2'))


class LanguageAdmin(VersionAdmin):
    fields = ('key', 'name', 'short_name', 'common_name', 'ace', 'pygments', 'info', 'description', 'problems')
    list_display = ('key', 'name', 'common_name', 'info')
    form = LanguageForm

    if AdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': AdminPagedownWidget},
        }

    def save_model(self, request, obj, form, change):
        super(LanguageAdmin, self).save_model(request, obj, form, change)
        obj.problem_set = Problem.objects.exclude(id__in=form.cleaned_data['problems'].values('id'))

    def get_form(self, request, obj=None, **kwargs):
        self.form.base_fields['problems'].initial = \
            Problem.objects.exclude(id__in=obj.problem_set.values('id')).values_list('pk', flat=True) if obj else []
        return super(LanguageAdmin, self).get_form(request, obj, **kwargs)


class ProblemGroupForm(ModelForm):
    problems = ModelMultipleChoiceField(
        label=_('Included problems'),
        queryset=Problem.objects.all(),
        required=False,
        help_text=_('These problems are included in this group of problems'),
        widget=HeavySelect2MultipleWidget(data_view='problem_select2'))


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
        label=_('Included problems'),
        queryset=Problem.objects.all(),
        required=False,
        help_text=_('These problems are included in this type of problems'),
        widget=HeavySelect2MultipleWidget(data_view='problem_select2'))


class ProblemTypeAdmin(admin.ModelAdmin):
    fields = ('name', 'full_name', 'problems')
    form = ProblemTypeForm

    def save_model(self, request, obj, form, change):
        super(ProblemTypeAdmin, self).save_model(request, obj, form, change)
        obj.problem_set = form.cleaned_data['problems']
        obj.save()

    def get_form(self, request, obj=None, **kwargs):
        self.form.base_fields['problems'].initial = [o.pk for o in obj.problem_set.all()] if obj else []
        return super(ProblemTypeAdmin, self).get_form(request, obj, **kwargs)


class NavigationBarAdmin(MPTTModelAdmin, SortableModelAdmin):
    list_display = ('label', 'key', 'path')
    fields = ('key', 'label', 'path', 'order', 'regex', 'parent')
    list_editable = ()  # Bug in SortableModelAdmin: 500 without list_editable being set
    mptt_level_indent = 20
    sortable = 'order'

    def __init__(self, *args, **kwargs):
        super(NavigationBarAdmin, self).__init__(*args, **kwargs)
        self.__save_model_calls = 0

    def save_model(self, request, obj, form, change):
        self.__save_model_calls += 1
        return super(NavigationBarAdmin, self).save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        self.__save_model_calls = 0
        with NavigationBar.objects.disable_mptt_updates():
            result = super(NavigationBarAdmin, self).changelist_view(request, extra_context)
        if self.__save_model_calls:
            with LockModel(write=(NavigationBar,)):
                NavigationBar.objects.rebuild()
        return result


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
        widgets = {
            'auth_key': GenerateKeyTextInput(),
        }


class JudgeAdmin(VersionAdmin):
    form = JudgeAdminForm
    readonly_fields = ('created', 'online', 'start_time', 'ping', 'load', 'last_ip', 'runtimes', 'problems')
    fieldsets = (
        (None, {'fields': ('name', 'auth_key')}),
        (_('Description'), {'fields': ('description',)}),
        (_('Information'), {'fields': ('created', 'online', 'last_ip', 'start_time', 'ping', 'load')}),
        (_('Capabilities'), {'fields': ('runtimes', 'problems')}),
    )
    list_display = ('name', 'online', 'start_time', 'ping', 'load', 'last_ip')
    ordering = ['-online', 'name']

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


class ContestTagForm(ModelForm):
    contests = ModelMultipleChoiceField(
        label=_('Included contests'),
        queryset=Contest.objects.all(),
        required=False,
        widget=HeavySelect2MultipleWidget(data_view='contest_select2'))


class ContestTagAdmin(admin.ModelAdmin):
    fields = ('name', 'color', 'description', 'contests')
    list_display = ('name', 'color')
    actions_on_top = True
    actions_on_bottom = True
    form = ContestTagForm

    if AdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': AdminPagedownWidget},
        }

    def save_model(self, request, obj, form, change):
        super(ContestTagAdmin, self).save_model(request, obj, form, change)
        obj.contests = form.cleaned_data['contests']

    def get_form(self, request, obj=None, **kwargs):
        form = super(ContestTagAdmin, self).get_form(request, obj, **kwargs)
        if obj is not None:
            form.base_fields['contests'].initial = obj.contests.all()
        return form


class ContestProblemInlineForm(ModelForm):
    class Meta:
        widgets = {
            'problem': HeavySelect2Widget(data_view='problem_select2'),
        }


class ContestProblemInline(SortableTabularInline):
    model = ContestProblem
    verbose_name = _('Problem')
    verbose_name_plural = 'Problems'
    fields = ('problem', 'points', 'partial', 'output_prefix_override')
    form = ContestProblemInlineForm
    sortable = 'order'
    if SortableTabularInline is admin.TabularInline:
        fields += ('order',)


class ContestForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ContestForm, self).__init__(*args, **kwargs)
        if 'rate_exclude' in self.fields:
            self.fields['rate_exclude'].queryset = \
                Profile.objects.filter(contest_history__contest=self.instance).distinct()

    class Meta:
        widgets = {
            'organizers': HeavySelect2MultipleWidget(data_view='profile_select2'),
            'organizations': HeavySelect2MultipleWidget(data_view='organization_select2'),
            'tags': Select2MultipleWidget
        }

        if MathJaxAdminPagedownWidget is not None:
            widgets['description'] = MathJaxAdminPagedownWidget


class ContestAdmin(VersionAdmin):
    fieldsets = (
        (None, {'fields': ('key', 'name', 'organizers', 'is_public', 'hide_problem_tags', 'run_pretests_only')}),
        (_('Scheduling'), {'fields': ('start_time', 'end_time', 'time_limit')}),
        (_('Details'), {'fields': ('description', 'og_image', 'tags', 'summary')}),
        (_('Rating'), {'fields': ('is_rated', 'rate_all', 'rate_exclude')}),
        (_('Organization'), {'fields': ('is_private', 'organizations')}),
    )
    list_display = ('key', 'name', 'is_public', 'is_rated', 'start_time', 'end_time', 'time_limit', 'user_count')
    actions = ['make_public', 'make_private']
    inlines = [ContestProblemInline]
    actions_on_top = True
    actions_on_bottom = True
    form = ContestForm
    change_list_template = 'admin/judge/contest/change_list.html'
    filter_horizontal = ['rate_exclude']

    def make_public(self, request, queryset):
        count = queryset.update(is_public=True)
        self.message_user(request, ungettext('%d contest successfully marked as public.',
                                             '%d contests successfully marked as public.',
                                             count) % count)

    make_public.short_description = _('Mark contests as public')

    def make_private(self, request, queryset):
        count = queryset.update(is_public=False)
        self.message_user(request, ungettext('%d contest successfully marked as private.',
                                             '%d contests successfully marked as private.',
                                             count) % count)

    make_private.short_description = _('Mark contests as private')

    def get_queryset(self, request):
        queryset = Contest.objects.all()
        if request.user.has_perm('judge.edit_all_contest'):
            return queryset
        else:
            return queryset.filter(organizers__id=request.user.profile.id)

    def get_readonly_fields(self, request, obj=None):
        if request.user.has_perm('judge.contest_rating'):
            return []
        return ['is_rated', 'rate_all', 'rate_exclude']

    def has_change_permission(self, request, obj=None):
        if not request.user.has_perm('judge.edit_own_contest'):
            return False
        if request.user.has_perm('judge.edit_all_contest') or obj is None:
            return True
        return obj.organizers.filter(id=request.user.profile.id).exists()

    def get_urls(self):
        return [
                   url(r'^rate/all/$', self.rate_all_view, name='judge_contest_rate_all'),
                   url(r'^(\d+)/rate/$', self.rate_view, name='judge_contest_rate')
               ] + super(ContestAdmin, self).get_urls()

    def rate_all_view(self, request):
        if not request.user.has_perm('judge.contest_rating'):
            raise PermissionDenied()
        with transaction.atomic():
            if connection.vendor == 'sqlite':
                Rating.objects.all().delete()
            else:
                cursor = connection.cursor()
                cursor.execute('TRUNCATE TABLE `%s`' % Rating._meta.db_table)
                cursor.close()
            Profile.objects.update(rating=None)
            for contest in Contest.objects.filter(is_rated=True).order_by('end_time'):
                rate_contest(contest)
        return HttpResponseRedirect(reverse('admin:judge_contest_changelist'))

    def rate_view(self, request, id):
        if not request.user.has_perm('judge.contest_rating'):
            raise PermissionDenied()
        contest = get_object_or_404(Contest, id=id)
        if not contest.is_rated:
            raise Http404()
        with transaction.atomic():
            Rating.objects.filter(contest__end_time__gte=contest.end_time).delete()
            for contest in Contest.objects.filter(is_rated=True, end_time__gte=contest.end_time).order_by('end_time'):
                rate_contest(contest)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('admin:judge_contest_changelist')))

    def get_form(self, *args, **kwargs):
        form = super(ContestAdmin, self).get_form(*args, **kwargs)
        perms = ('edit_own_contest', 'edit_all_contest')
        form.base_fields['organizers'].queryset = Profile.objects.filter(
            Q(user__is_superuser=True) |
            Q(user__groups__permissions__codename__in=perms) |
            Q(user__user_permissions__codename__in=perms)
        ).distinct()
        return form


class ContestParticipationForm(ModelForm):
    class Meta:
        widgets = {
            'contest': Select2Widget(),
            'user': HeavySelect2Widget(data_view='profile_select2'),
        }


class ContestParticipationAdmin(admin.ModelAdmin):
    fields = ('contest', 'user', 'real_start', 'virtual')
    list_display = ('contest', 'username', 'show_virtual', 'real_start', 'score', 'cumtime')
    actions = ['recalculate_points', 'recalculate_cumtime']
    actions_on_bottom = actions_on_top = True
    search_fields = ('contest__key', 'contest__name', 'user__user__username', 'user__name')
    form = ContestParticipationForm

    def get_queryset(self, request):
        return super(ContestParticipationAdmin, self).get_queryset(request).only(
            'contest__name', 'user__user__username', 'user__name', 'real_start', 'score', 'cumtime', 'virtual'
        )

    def username(self, obj):
        return obj.user.long_display_name

    username.admin_order_field = 'user__user__username'

    def show_virtual(self, obj):
        return obj.virtual or '-'

    show_virtual.short_description = _('virtual')
    show_virtual.admin_order_field = 'virtual'

    def recalculate_points(self, request, queryset):
        count = 0
        for participation in queryset:
            participation.recalculate_score()
            count += 1
        self.message_user(request, ungettext('%d participation have scores recalculated.',
                                             '%d participations have scores recalculated.',
                                             count) % count)

    recalculate_points.short_description = _('Recalculate scores')

    def recalculate_cumtime(self, request, queryset):
        count = 0
        for participation in queryset:
            participation.update_cumtime()
            count += 1
        self.message_user(request, ungettext('%d participation have times recalculated.',
                                             '%d participations have times recalculated.',
                                             count) % count)

    recalculate_cumtime.short_description = _('Recalculate cumulative time')


class OrganizationForm(ModelForm):
    class Meta:
        widgets = {
            'admins': HeavySelect2MultipleWidget(data_view='profile_select2'),
            'registrant': HeavySelect2Widget(data_view='profile_select2'),
        }


class OrganizationAdmin(VersionAdmin):
    readonly_fields = ('creation_date',)
    fields = ('name', 'key', 'short_name', 'is_open', 'about', 'slots', 'registrant', 'creation_date', 'admins')
    list_display = ('name', 'key', 'short_name', 'is_open', 'slots', 'registrant', 'show_public')
    actions_on_top = True
    actions_on_bottom = True
    form = OrganizationForm

    def show_public(self, obj):
        format = '<a href="{0}" style="white-space:nowrap;">%s</a>' % ugettext('View on site')
        return format_html(format, obj.get_absolute_url())

    show_public.short_description = ''

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if not request.user.has_perm('judge.organization_admin'):
            return fields + ('registrant', 'admins', 'is_open', 'slots')
        return fields

    if MathJaxAdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': MathJaxAdminPagedownWidget},
        }

    def get_queryset(self, request):
        queryset = Organization.objects.all()
        if request.user.has_perm('judge.edit_all_organization'):
            return queryset
        else:
            return queryset.filter(admins=request.user.profile.id)

    def has_change_permission(self, request, obj=None):
        if not request.user.has_perm('judge.change_organization'):
            return False
        if request.user.has_perm('judge.edit_all_organization') or obj is None:
            return True
        return obj.admins.filter(id=request.user.profile.id).exists()


class BlogPostAdmin(VersionAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'authors', 'visible', 'sticky', 'publish_on')}),
        (_('Content'), {'fields': ('content', 'og_image',)}),
        (_('Summary'), {'classes': ('collapse',), 'fields': ('summary',)}),
    )
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('id', 'title', 'visible', 'sticky', 'publish_on')
    list_display_links = ('id', 'title')
    ordering = ('-publish_on',)
    form = BlogPostForm

    if AdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': AdminPagedownWidget},
        }

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or (request.user.has_perm('judge.see_hidden_post') and
                (obj is None or obj.authors.filter(id=request.user.profile.id).exists()))


class SolutionForm(ModelForm):
    class Meta:
        widgets = {
            'problem': HeavySelect2Widget(data_view='problem_select2', attrs={'style': 'width: 250px'}),
        }


class SolutionAdmin(VersionAdmin):
    fields = ('url', 'title', 'is_public', 'publish_on', 'problem', 'content')
    list_display = ('title', 'url', 'problem_link', 'show_public')
    search_fields = ('url', 'title')
    form = SolutionForm

    def show_public(self, obj):
        format = '<a href="{0}" style="white-space:nowrap;">%s</a>' % ugettext('View on site')
        return format_html(format, obj.get_absolute_url())

    show_public.short_description = ''

    def problem_link(self, obj):
        if obj.problem is None:
            return 'N/A'
        return format_html(u'<a href="{}">{}</a>', reverse('admin:judge_problem_change', args=[obj.problem_id]),
                           obj.problem.name)

    problem_link.admin_order_field = 'problem__name'

    if MathJaxAdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': MathJaxAdminPagedownWidget},
        }


class LicenseAdmin(admin.ModelAdmin):
    fields = ('key', 'link', 'name', 'display', 'icon', 'text')
    list_display = ('name', 'key')

    if MathJaxAdminPagedownWidget is not None:
        formfield_overrides = {
            TextField: {'widget': MathJaxAdminPagedownWidget},
        }


class OrganizationRequestAdmin(admin.ModelAdmin):
    list_display = ('username', 'organization', 'state', 'time')
    readonly_fields = ('user', 'organization')

    def username(self, obj):
        return obj.user.long_display_name

    username.admin_order_field = 'user__user__username'


admin.site.register(Language, LanguageAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Problem, ProblemAdmin)
admin.site.register(ProblemGroup, ProblemGroupAdmin)
admin.site.register(ProblemType, ProblemTypeAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(MiscConfig)
admin.site.register(NavigationBar, NavigationBarAdmin)
admin.site.register(Judge, JudgeAdmin)
admin.site.register(Contest, ContestAdmin)
admin.site.register(ContestTag, ContestTagAdmin)
admin.site.register(ContestParticipation, ContestParticipationAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(BlogPost, BlogPostAdmin)
admin.site.register(Solution, SolutionAdmin)
admin.site.register(License, LicenseAdmin)
admin.site.register(OrganizationRequest, OrganizationRequestAdmin)
