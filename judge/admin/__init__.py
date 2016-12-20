from django.contrib import admin
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import TextField
from django.forms import ModelForm, TextInput
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext
from mptt.admin import MPTTModelAdmin
from reversion.admin import VersionAdmin

from judge.admin.comments import CommentAdmin
from judge.admin.contest import ContestTagAdmin, ContestAdmin, ContestParticipationAdmin
from judge.admin.problem import ProblemAdmin
from judge.admin.profile import ProfileAdmin
from judge.admin.submission import SubmissionAdmin
from judge.admin.taxon import LanguageAdmin, ProblemGroupAdmin, ProblemTypeAdmin
from judge.dblock import LockModel
from judge.models import Language, Profile, Problem, ProblemGroup, ProblemType, Submission, Comment, \
    MiscConfig, Judge, NavigationBar, Contest, ContestParticipation, Organization, BlogPost, \
    Solution, License, OrganizationRequest, \
    ContestTag
from judge.widgets import AdminPagedownWidget, MathJaxAdminPagedownWidget, \
    HeavyPreviewAdminPageDownWidget, HeavySelect2Widget, HeavySelect2MultipleWidget

# try:
#    from suit.admin import SortableModelAdmin, SortableTabularInline
# except ImportError:
SortableModelAdmin = object
SortableTabularInline = admin.TabularInline


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


class BlogPostForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(BlogPostForm, self).__init__(*args, **kwargs)
        self.fields['authors'].widget.can_add_related = False

    class Meta:
        widgets = {
            'authors': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
        }

        if HeavyPreviewAdminPageDownWidget is not None:
            widgets['content'] = HeavyPreviewAdminPageDownWidget(preview=reverse_lazy('blog_preview'))
            widgets['summary'] = HeavyPreviewAdminPageDownWidget(preview=reverse_lazy('blog_preview'))


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
