from django.conf import settings
from django.conf.urls import url
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models import Q, TextField
from django.forms import ModelForm, ModelMultipleChoiceField
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _, ugettext, ungettext
from reversion.admin import VersionAdmin

from judge.models import Contest, ContestProblem, ContestSubmission, Profile, Rating
from judge.ratings import rate_contest
from judge.widgets import AdminPagedownWidget, HeavyPreviewAdminPageDownWidget, HeavySelect2MultipleWidget, \
    HeavySelect2Widget, Select2MultipleWidget, Select2Widget


class HeavySelect2Widget(HeavySelect2Widget):
    @property
    def is_hidden(self):
        return False


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
        obj.contests.set(form.cleaned_data['contests'])

    def get_form(self, request, obj=None, **kwargs):
        form = super(ContestTagAdmin, self).get_form(request, obj, **kwargs)
        if obj is not None:
            form.base_fields['contests'].initial = obj.contests.all()
        return form


class ContestProblemInlineForm(ModelForm):
    class Meta:
        widgets = {'problem': HeavySelect2Widget(data_view='problem_select2')}


class ContestProblemInline(admin.TabularInline):
    model = ContestProblem
    verbose_name = _('Problem')
    verbose_name_plural = 'Problems'
    fields = ('problem', 'points', 'partial', 'is_pretested', 'max_submissions', 'output_prefix_override', 'order',
              'rejudge_column')
    readonly_fields = ('rejudge_column',)
    form = ContestProblemInlineForm

    def rejudge_column(self, obj):
        if obj.id is None:
            return ''
        return format_html('<a class="button rejudge-link" href="{}">Rejudge</a>',
                           reverse('admin:judge_contest_rejudge', args=(obj.contest.id, obj.id)))
    rejudge_column.short_description = ''


class ContestForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ContestForm, self).__init__(*args, **kwargs)
        if 'rate_exclude' in self.fields:
            if self.instance and self.instance.id:
                self.fields['rate_exclude'].queryset = \
                    Profile.objects.filter(contest_history__contest=self.instance).distinct()
            else:
                self.fields['rate_exclude'].queryset = Profile.objects.none()
        self.fields['banned_users'].widget.can_add_related = False

    def clean(self):
        cleaned_data = super(ContestForm, self).clean()
        cleaned_data['banned_users'].filter(current_contest__contest=self.instance).update(current_contest=None)

    class Meta:
        widgets = {
            'organizers': HeavySelect2MultipleWidget(data_view='profile_select2'),
            'private_contestants': HeavySelect2MultipleWidget(data_view='profile_select2',
                                                              attrs={'style': 'width: 100%'}),
            'organizations': HeavySelect2MultipleWidget(data_view='organization_select2'),
            'tags': Select2MultipleWidget,
            'banned_users': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
        }

        if HeavyPreviewAdminPageDownWidget is not None:
            widgets['description'] = HeavyPreviewAdminPageDownWidget(preview=reverse_lazy('contest_preview'))


class ContestAdmin(VersionAdmin):
    fieldsets = (
        (None, {'fields': ('key', 'name', 'organizers')}),
        (_('Settings'), {'fields': ('is_visible', 'use_clarifications', 'hide_problem_tags', 'hide_scoreboard',
                                    'run_pretests_only')}),
        (_('Scheduling'), {'fields': ('start_time', 'end_time', 'time_limit')}),
        (_('Details'), {'fields': ('description', 'og_image', 'logo_override_image', 'tags', 'summary')}),
        (_('Format'), {'fields': ('format_name', 'format_config')}),
        (_('Rating'), {'fields': ('is_rated', 'rate_all', 'rating_floor', 'rating_ceiling', 'rate_exclude')}),
        (_('Access'), {'fields': ('access_code', 'is_private', 'private_contestants', 'is_organization_private',
                                  'organizations')}),
        (_('Justice'), {'fields': ('banned_users',)}),
    )
    list_display = ('key', 'name', 'is_visible', 'is_rated', 'start_time', 'end_time', 'time_limit', 'user_count')
    actions = ['make_visible', 'make_hidden']
    inlines = [ContestProblemInline]
    actions_on_top = True
    actions_on_bottom = True
    form = ContestForm
    change_list_template = 'admin/judge/contest/change_list.html'
    filter_horizontal = ['rate_exclude']
    date_hierarchy = 'start_time'

    def get_queryset(self, request):
        queryset = Contest.objects.all()
        if request.user.has_perm('judge.edit_all_contest'):
            return queryset
        else:
            return queryset.filter(organizers__id=request.profile.id)

    def get_readonly_fields(self, request, obj=None):
        readonly = []
        if not request.user.has_perm('judge.contest_rating'):
            readonly += ['is_rated', 'rate_all', 'rate_exclude']
        if not request.user.has_perm('judge.contest_access_code'):
            readonly += ['access_code']
        if not request.user.has_perm('judge.create_private_contest'):
            readonly += ['is_private', 'private_contestants', 'is_organization_private', 'organizations']
        return readonly

    def has_change_permission(self, request, obj=None):
        if not request.user.has_perm('judge.edit_own_contest'):
            return False
        if request.user.has_perm('judge.edit_all_contest') or obj is None:
            return True
        return obj.organizers.filter(id=request.profile.id).exists()

    def make_visible(self, request, queryset):
        count = queryset.update(is_visible=True)
        self.message_user(request, ungettext('%d contest successfully marked as visible.',
                                             '%d contests successfully marked as visible.',
                                             count) % count)
    make_visible.short_description = _('Mark contests as visible')

    def make_hidden(self, request, queryset):
        count = queryset.update(is_visible=False)
        self.message_user(request, ungettext('%d contest successfully marked as hidden.',
                                             '%d contests successfully marked as hidden.',
                                             count) % count)
    make_hidden.short_description = _('Mark contests as hidden')

    def get_urls(self):
        return [
            url(r'^rate/all/$', self.rate_all_view, name='judge_contest_rate_all'),
            url(r'^(\d+)/rate/$', self.rate_view, name='judge_contest_rate'),
            url(r'^(\d+)/judge/(\d+)/$', self.rejudge_view, name='judge_contest_rejudge'),
        ] + super(ContestAdmin, self).get_urls()

    def rejudge_view(self, request, contest_id, problem_id):
        if not request.user.has_perm('judge.rejudge_submission'):
            self.message_user(request, ugettext('You do not have the permission to rejudge submissions.'),
                              level=messages.ERROR)
            return

        queryset = ContestSubmission.objects.filter(problem_id=problem_id).select_related('submission')
        if not request.user.has_perm('judge.rejudge_submission_lot') and \
                len(queryset) > settings.DMOJ_SUBMISSIONS_REJUDGE_LIMIT:
            self.message_user(request, ugettext('You do not have the permission to rejudge THAT many submissions.'),
                              level=messages.ERROR)
            return

        for model in queryset:
            model.submission.judge(rejudge=True)

        self.message_user(request, ungettext('%d submission was successfully scheduled for rejudging.',
                                             '%d submissions were successfully scheduled for rejudging.',
                                             len(queryset)) % len(queryset))
        return HttpResponseRedirect(reverse('admin:judge_contest_change', args=(contest_id,)))

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
            Q(user__user_permissions__codename__in=perms),
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
    actions = ['recalculate_results']
    actions_on_bottom = actions_on_top = True
    search_fields = ('contest__key', 'contest__name', 'user__user__username')
    form = ContestParticipationForm
    date_hierarchy = 'real_start'

    def get_queryset(self, request):
        return super(ContestParticipationAdmin, self).get_queryset(request).only(
            'contest__name', 'contest__format_name', 'contest__format_config',
            'user__user__username', 'real_start', 'score', 'cumtime', 'virtual',
        )

    def recalculate_results(self, request, queryset):
        count = 0
        for participation in queryset:
            participation.recompute_results()
            count += 1
        self.message_user(request, ungettext('%d participation recalculated.',
                                             '%d participations recalculated.',
                                             count) % count)
    recalculate_results.short_description = _('Recalculate results')

    def username(self, obj):
        return obj.user.username
    username.short_description = _('username')
    username.admin_order_field = 'user__user__username'

    def show_virtual(self, obj):
        return obj.virtual or '-'
    show_virtual.short_description = _('virtual')
    show_virtual.admin_order_field = 'virtual'
