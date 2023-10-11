from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as OldUserAdmin
from django.forms import ModelForm
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext, gettext_lazy as _, ngettext
from reversion.admin import VersionAdmin

from django_ace import AceWidget
from judge.models import Profile, WebAuthnCredential
from judge.utils.views import NoBatchDeleteMixin
from judge.widgets import AdminMartorWidget, AdminSelect2Widget


class ProfileForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        if 'current_contest' in self.base_fields:
            # form.fields['current_contest'] does not exist when the user has only view permission on the model.
            self.fields['current_contest'].queryset = self.instance.contest_history.select_related('contest') \
                .only('contest__name', 'user_id', 'virtual')
            self.fields['current_contest'].label_from_instance = \
                lambda obj: '%s v%d' % (obj.contest.name, obj.virtual) if obj.virtual else obj.contest.name

    class Meta:
        widgets = {
            'timezone': AdminSelect2Widget,
            'language': AdminSelect2Widget,
            'ace_theme': AdminSelect2Widget,
            'current_contest': AdminSelect2Widget,
            'about': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('profile_preview')}),
        }


class TimezoneFilter(admin.SimpleListFilter):
    title = _('timezone')
    parameter_name = 'timezone'

    def lookups(self, request, model_admin):
        return Profile.objects.values_list('timezone', 'timezone').distinct().order_by('timezone')

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(timezone=self.value())


class WebAuthnInline(admin.TabularInline):
    model = WebAuthnCredential
    readonly_fields = ('cred_id', 'public_key', 'counter')
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False


class ProfileAdmin(NoBatchDeleteMixin, VersionAdmin):
    fields = ('user', 'display_rank', 'about', 'organizations', 'timezone', 'language', 'ace_theme',
              'math_engine', 'last_access', 'ip', 'mute', 'is_unlisted', 'is_banned_from_problem_voting',
              'username_display_override', 'notes', 'is_totp_enabled', 'user_script', 'current_contest')
    readonly_fields = ('user',)
    list_display = ('admin_user_admin', 'email', 'is_totp_enabled', 'timezone_full',
                    'date_joined', 'last_access', 'ip', 'show_public')
    ordering = ('user__username',)
    search_fields = ('user__username', 'ip', 'user__email')
    list_filter = ('language', TimezoneFilter)
    actions = ('recalculate_points',)
    actions_on_top = True
    actions_on_bottom = True
    form = ProfileForm
    inlines = [WebAuthnInline]

    def has_add_permission(self, request, obj=None):
        return False

    # We can't use has_delete_permission here because we still want user profiles to be
    # deleteable through related objects (i.e. User). Thus, we simply hide the delete button.
    # If an admin wants to go directly to the delete endpoint to delete a profile, more
    # power to them.
    def render_change_form(self, request, context, **kwargs):
        context['show_delete'] = False
        return super().render_change_form(request, context, **kwargs)

    def get_queryset(self, request):
        return super(ProfileAdmin, self).get_queryset(request).select_related('user')

    def get_fields(self, request, obj=None):
        if request.user.has_perm('judge.totp'):
            fields = list(self.fields)
            fields.insert(fields.index('is_totp_enabled') + 1, 'totp_key')
            fields.insert(fields.index('totp_key') + 1, 'scratch_codes')
            return tuple(fields)
        else:
            return self.fields

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if not request.user.has_perm('judge.totp'):
            fields += ('is_totp_enabled',)
        return fields

    @admin.display(description='')
    def show_public(self, obj):
        return format_html('<a href="{0}" style="white-space:nowrap;">{1}</a>',
                           obj.get_absolute_url(), gettext('View on site'))

    @admin.display(description=_('user'), ordering='user__username')
    def admin_user_admin(self, obj):
        return obj.username

    @admin.display(description=_('email'), ordering='user__email')
    def email(self, obj):
        return obj.user.email

    @admin.display(description=_('timezone'), ordering='timezone')
    def timezone_full(self, obj):
        return obj.timezone

    @admin.display(description=_('date joined'), ordering='user__date_joined')
    def date_joined(self, obj):
        return obj.user.date_joined

    @admin.display(description=_('Recalculate scores'))
    def recalculate_points(self, request, queryset):
        count = 0
        for profile in queryset:
            profile.calculate_points()
            count += 1
        self.message_user(request, ngettext('%d user had scores recalculated.',
                                            '%d users had scores recalculated.',
                                            count) % count)

    def get_form(self, request, obj=None, **kwargs):
        form = super(ProfileAdmin, self).get_form(request, obj, **kwargs)
        if 'user_script' in form.base_fields:
            # form.base_fields['user_script'] does not exist when the user has only view permission on the model.
            form.base_fields['user_script'].widget = AceWidget(
                mode='javascript', theme=request.profile.resolved_ace_theme,
            )
        return form


class UserAdmin(OldUserAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            Profile.objects.create(user=obj)
