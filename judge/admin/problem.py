from operator import attrgetter

from django import forms
from django.contrib import admin
from django.db import connection
from django.db.models import Q
from django.forms import ModelForm
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext, gettext_lazy as _, ungettext
from reversion.admin import VersionAdmin

from judge.models import LanguageLimit, Problem, ProblemClarification, ProblemTranslation, Profile, Solution
from judge.widgets import CheckboxSelectMultipleWithSelectAll, HeavyPreviewAdminPageDownWidget, \
    HeavyPreviewPageDownWidget, HeavySelect2MultipleWidget, Select2MultipleWidget, Select2Widget


class ProblemForm(ModelForm):
    change_message = forms.CharField(max_length=256, label='Edit reason', required=False)

    def __init__(self, *args, **kwargs):
        super(ProblemForm, self).__init__(*args, **kwargs)
        self.fields['authors'].widget.can_add_related = False
        self.fields['curators'].widget.can_add_related = False
        self.fields['testers'].widget.can_add_related = False
        self.fields['banned_users'].widget.can_add_related = False
        self.fields['change_message'].widget.attrs.update({
            'placeholder': gettext('Describe the changes you made (optional)')
        })

    class Meta:
        widgets = {
            'authors': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
            'curators': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
            'testers': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
            'banned_users': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
            'organizations': HeavySelect2MultipleWidget(data_view='organization_select2',
                                                        attrs={'style': 'width: 100%'}),
            'types': Select2MultipleWidget,
            'group': Select2Widget,
        }
        if HeavyPreviewAdminPageDownWidget is not None:
            widgets['description'] = HeavyPreviewAdminPageDownWidget(preview=reverse_lazy('problem_preview'))


class ProblemCreatorListFilter(admin.SimpleListFilter):
    title = parameter_name = 'creator'

    def lookups(self, request, model_admin):
        queryset = Profile.objects.exclude(authored_problems=None).values_list('user__username', flat=True)
        return [(name, name) for name in queryset]

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(authors__user__username=self.value())


class LanguageLimitInlineForm(ModelForm):
    class Meta:
        widgets = {'language': Select2Widget}


class LanguageLimitInline(admin.TabularInline):
    model = LanguageLimit
    fields = ('language', 'time_limit', 'memory_limit')
    form = LanguageLimitInlineForm


class ProblemClarificationForm(ModelForm):
    class Meta:
        if HeavyPreviewPageDownWidget is not None:
            widgets = {'description': HeavyPreviewPageDownWidget(preview=reverse_lazy('comment_preview'))}


class ProblemClarificationInline(admin.StackedInline):
    model = ProblemClarification
    fields = ('description',)
    form = ProblemClarificationForm
    extra = 0


class ProblemSolutionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProblemSolutionForm, self).__init__(*args, **kwargs)
        self.fields['authors'].widget.can_add_related = False

    class Meta:
        widgets = {
            'authors': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
        }

        if HeavyPreviewAdminPageDownWidget is not None:
            widgets['content'] = HeavyPreviewAdminPageDownWidget(preview=reverse_lazy('solution_preview'))


class ProblemSolutionInline(admin.StackedInline):
    model = Solution
    fields = ('is_public', 'publish_on', 'authors', 'content')
    form = ProblemSolutionForm
    extra = 0


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
            'fields': (
                'code', 'name', 'is_public', 'is_manually_managed', 'date', 'authors', 'curators', 'testers',
                'is_organization_private', 'organizations',
                'description',
                'license')
        }),
        (_('Social Media'), {'classes': ('collapse',), 'fields': ('og_image', 'summary')}),
        (_('Taxonomy'), {'fields': ('types', 'group')}),
        (_('Points'), {'fields': (('points', 'partial'), 'short_circuit')}),
        (_('Limits'), {'fields': ('time_limit', 'memory_limit')}),
        (_('Language'), {'fields': ('allowed_languages',)}),
        (_('Justice'), {'fields': ('banned_users',)}),
        (_('History'), {'fields': ('change_message',)})
    )
    list_display = ['code', 'name', 'show_authors', 'points', 'is_public', 'show_public']
    ordering = ['code']
    search_fields = ('code', 'name', 'authors__user__username', 'curators__user__username')
    inlines = [LanguageLimitInline, ProblemClarificationInline, ProblemSolutionInline, ProblemTranslationInline]
    list_max_show_all = 1000
    actions_on_top = True
    actions_on_bottom = True
    list_filter = ('is_public', ProblemCreatorListFilter)
    form = ProblemForm
    date_hierarchy = 'date'

    def get_actions(self, request):
        actions = super(ProblemAdmin, self).get_actions(request)

        if request.user.has_perm('judge.change_public_visibility'):
            func, name, desc = self.get_action('make_public')
            actions[name] = (func, name, desc)

            func, name, desc = self.get_action('make_private')
            actions[name] = (func, name, desc)

        return actions

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if not request.user.has_perm('judge.change_public_visibility'):
            fields += ('is_public',)
        if not request.user.has_perm('judge.change_manually_managed'):
            fields += ('is_manually_managed',)
        return fields

    def show_authors(self, obj):
        return ', '.join(map(attrgetter('user.username'), obj.authors.all()))

    show_authors.short_description = _('Authors')

    def show_public(self, obj):
        return format_html('<a href="{1}">{0}</a>', gettext('View on site'), obj.get_absolute_url())

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
            '''.format(', '.join(['%s'] * len(ids)), sign), list(ids))

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
            access |= Q(authors__id=request.profile.id) | Q(curators__id=request.profile.id)
        return queryset.filter(access).distinct() if access else queryset.none()

    def has_change_permission(self, request, obj=None):
        if request.user.has_perm('judge.edit_all_problem') or obj is None:
            return True
        if request.user.has_perm('judge.edit_public_problem') and obj.is_public:
            return True
        if not request.user.has_perm('judge.edit_own_problem'):
            return False
        return obj.is_editor(request.profile)

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
