from functools import partial
from operator import itemgetter

from django.conf import settings
from django.conf.urls import url
from django.contrib import admin, messages
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.utils.translation import gettext, gettext_lazy as _, pgettext, ungettext

from django_ace import AceWidget
from judge.models import ContestParticipation, ContestProblem, ContestSubmission, Profile, Submission, \
    SubmissionSource, SubmissionTestCase
from judge.utils.raw_sql import use_straight_join


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

                def label(obj):
                    return obj.contest.name
            elif db_field.name == 'problem':
                kwargs['queryset'] = ContestProblem.objects.filter(problem=submission.problem) \
                    .only('id', 'problem__name', 'contest__name')

                def label(obj):
                    return pgettext('contest problem', '%(problem)s in %(contest)s') % {
                        'problem': obj.problem.name, 'contest': obj.contest.name,
                    }
        field = super(ContestSubmissionInline, self).formfield_for_dbfield(db_field, **kwargs)
        if label is not None:
            field.label_from_instance = label
        return field


class SubmissionSourceInline(admin.StackedInline):
    fields = ('source',)
    model = SubmissionSource
    can_delete = False
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        kwargs.setdefault('widgets', {})['source'] = AceWidget(mode=obj and obj.language.ace,
                                                               theme=request.profile.ace_theme)
        return super().get_formset(request, obj, **kwargs)


class SubmissionAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'problem', 'date', 'judged_date')
    fields = ('user', 'problem', 'date', 'judged_date', 'is_locked', 'time', 'memory', 'points', 'language', 'status',
              'result', 'case_points', 'case_total', 'judged_on', 'error')
    actions = ('judge', 'recalculate_score')
    list_display = ('id', 'problem_code', 'problem_name', 'user_column', 'execution_time', 'pretty_memory',
                    'points', 'language_column', 'status', 'result', 'judge_column')
    list_filter = ('language', SubmissionStatusFilter, SubmissionResultFilter)
    search_fields = ('problem__code', 'problem__name', 'user__user__username')
    actions_on_top = True
    actions_on_bottom = True
    inlines = [SubmissionSourceInline, SubmissionTestCaseInline, ContestSubmissionInline]

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if not request.user.has_perm('judge.lock_submission'):
            fields += ('is_locked',)
        return fields

    def get_queryset(self, request):
        queryset = Submission.objects.select_related('problem', 'user__user', 'language').only(
            'problem__code', 'problem__name', 'user__user__username', 'language__name',
            'time', 'memory', 'points', 'status', 'result',
        )
        use_straight_join(queryset)
        if not request.user.has_perm('judge.edit_all_problem'):
            id = request.profile.id
            queryset = queryset.filter(Q(problem__authors__id=id) | Q(problem__curators__id=id)).distinct()
        return queryset

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if not request.user.has_perm('judge.edit_own_problem'):
            return False
        if request.user.has_perm('judge.edit_all_problem') or obj is None:
            return True
        return obj.problem.is_editor(request.profile)

    def lookup_allowed(self, key, value):
        return super(SubmissionAdmin, self).lookup_allowed(key, value) or key in ('problem__code',)

    def judge(self, request, queryset):
        if not request.user.has_perm('judge.rejudge_submission') or not request.user.has_perm('judge.edit_own_problem'):
            self.message_user(request, gettext('You do not have the permission to rejudge submissions.'),
                              level=messages.ERROR)
            return
        queryset = queryset.order_by('id')
        if not request.user.has_perm('judge.rejudge_submission_lot') and \
                queryset.count() > settings.DMOJ_SUBMISSIONS_REJUDGE_LIMIT:
            self.message_user(request, gettext('You do not have the permission to rejudge THAT many submissions.'),
                              level=messages.ERROR)
            return
        if not request.user.has_perm('judge.edit_all_problem'):
            id = request.profile.id
            queryset = queryset.filter(Q(problem__authors__id=id) | Q(problem__curators__id=id))
        judged = len(queryset)
        for model in queryset:
            model.judge(rejudge=True, batch_rejudge=True)
        self.message_user(request, ungettext('%d submission was successfully scheduled for rejudging.',
                                             '%d submissions were successfully scheduled for rejudging.',
                                             judged) % judged)
    judge.short_description = _('Rejudge the selected submissions')

    def recalculate_score(self, request, queryset):
        if not request.user.has_perm('judge.rejudge_submission'):
            self.message_user(request, gettext('You do not have the permission to rejudge submissions.'),
                              level=messages.ERROR)
            return
        submissions = list(queryset.defer(None).select_related(None).select_related('problem')
                           .only('points', 'case_points', 'case_total', 'problem__partial', 'problem__points'))
        for submission in submissions:
            submission.points = round(submission.case_points / submission.case_total * submission.problem.points
                                      if submission.case_total else 0, 1)
            if not submission.problem.partial and submission.points < submission.problem.points:
                submission.points = 0
            submission.save()
            submission.update_contest()

        for profile in Profile.objects.filter(id__in=queryset.values_list('user_id', flat=True).distinct()):
            profile.calculate_points()
            cache.delete('user_complete:%d' % profile.id)
            cache.delete('user_attempted:%d' % profile.id)

        for participation in ContestParticipation.objects.filter(
                id__in=queryset.values_list('contest__participation_id')).prefetch_related('contest'):
            participation.recompute_results()

        self.message_user(request, ungettext('%d submission were successfully rescored.',
                                             '%d submissions were successfully rescored.',
                                             len(submissions)) % len(submissions))
    recalculate_score.short_description = _('Rescore the selected submissions')

    def problem_code(self, obj):
        return obj.problem.code
    problem_code.short_description = _('Problem code')
    problem_code.admin_order_field = 'problem__code'

    def problem_name(self, obj):
        return obj.problem.name
    problem_name.short_description = _('Problem name')
    problem_name.admin_order_field = 'problem__name'

    def user_column(self, obj):
        return obj.user.user.username
    user_column.admin_order_field = 'user__user__username'
    user_column.short_description = _('User')

    def execution_time(self, obj):
        return round(obj.time, 2) if obj.time is not None else 'None'
    execution_time.short_description = _('Time')
    execution_time.admin_order_field = 'time'

    def pretty_memory(self, obj):
        memory = obj.memory
        if memory is None:
            return gettext('None')
        if memory < 1000:
            return gettext('%d KB') % memory
        else:
            return gettext('%.2f MB') % (memory / 1024)
    pretty_memory.admin_order_field = 'memory'
    pretty_memory.short_description = _('Memory')

    def language_column(self, obj):
        return obj.language.name
    language_column.admin_order_field = 'language__name'
    language_column.short_description = _('Language')

    def judge_column(self, obj):
        return format_html('<input type="button" value="Rejudge" onclick="location.href=\'{}/judge/\'" />', obj.id)
    judge_column.short_description = ''

    def get_urls(self):
        return [
            url(r'^(\d+)/judge/$', self.judge_view, name='judge_submission_rejudge'),
        ] + super(SubmissionAdmin, self).get_urls()

    def judge_view(self, request, id):
        if not request.user.has_perm('judge.rejudge_submission') or not request.user.has_perm('judge.edit_own_problem'):
            raise PermissionDenied()
        submission = get_object_or_404(Submission, id=id)
        if not request.user.has_perm('judge.edit_all_problem') and \
                not submission.problem.is_editor(request.profile):
            raise PermissionDenied()
        submission.judge(rejudge=True)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
