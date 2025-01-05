from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.flatpages.admin import FlatPageAdmin as OldFlatPageAdmin
from django.contrib.flatpages.forms import FlatpageForm as OldFlatpageForm
from django.forms import ModelForm
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from mptt.admin import DraggableMPTTAdmin
from reversion.admin import VersionAdmin

from judge.dblock import LockModel
from judge.models import BlogPost, NavigationBar
from judge.widgets import AdminHeavySelect2MultipleWidget, AdminHeavySelect2Widget, AdminMartorWidget


class NavigationBarAdmin(DraggableMPTTAdmin):
    list_display = DraggableMPTTAdmin.list_display + ('key', 'linked_path')
    fields = ('key', 'label', 'path', 'order', 'regex', 'parent')
    list_editable = ()  # Bug in SortableModelAdmin: 500 without list_editable being set
    mptt_level_indent = 20
    sortable = 'order'

    def __init__(self, *args, **kwargs):
        super(NavigationBarAdmin, self).__init__(*args, **kwargs)
        self.__save_model_calls = 0

    @admin.display(description=_('link path'))
    def linked_path(self, obj):
        return format_html('<a href="{0}" target="_blank">{0}</a>', obj.path)

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


class FlatpageForm(OldFlatpageForm):
    class Meta(OldFlatpageForm.Meta):
        widgets = {'content': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('flatpage_preview')})}


class FlatPageAdmin(VersionAdmin, OldFlatPageAdmin):
    form = FlatpageForm


class BlogPostForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(BlogPostForm, self).__init__(*args, **kwargs)
        if 'authors' in self.fields:
            # self.fields['authors'] does not exist when the user has only view permission on the model.
            self.fields['authors'].widget.can_add_related = False

    class Meta:
        widgets = {
            'authors': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'content': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('blog_preview')}),
            'summary': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('blog_preview')}),
        }


class BlogPostAdmin(VersionAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'authors', 'visible', 'sticky', 'publish_on')}),
        (_('Content'), {'fields': ('content', 'og_image')}),
        (_('Summary'), {'classes': ('collapse',), 'fields': ('summary',)}),
    )
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('id', 'title', 'visible', 'sticky', 'publish_on')
    list_display_links = ('id', 'title')
    ordering = ('-publish_on',)
    form = BlogPostForm
    date_hierarchy = 'publish_on'

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return request.user.has_perm('judge.change_blogpost')
        return obj.is_editable_by(request.user)

    def get_readonly_fields(self, request, obj=None):
        if not request.user.has_perm('judge.change_post_visibility'):
            return ['visible']
        return []

    def get_queryset(self, request):
        queryset = BlogPost.objects.all()
        if not request.user.has_perm('judge.edit_all_post'):
            queryset = queryset.filter(authors=request.profile)
        return queryset


class SolutionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(SolutionForm, self).__init__(*args, **kwargs)
        self.fields['authors'].widget.can_add_related = False

    class Meta:
        widgets = {
            'authors': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'problem': AdminHeavySelect2Widget(data_view='problem_select2'),
            'content': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('solution_preview')}),
        }


class LicenseForm(ModelForm):
    class Meta:
        widgets = {'text': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('license_preview')})}


class LicenseAdmin(admin.ModelAdmin):
    fields = ('key', 'link', 'name', 'display', 'icon', 'text')
    list_display = ('name', 'key')
    form = LicenseForm


class UserListFilter(admin.SimpleListFilter):
    title = _('user')
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return User.objects.filter(is_staff=True).values_list('id', 'username')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_id=self.value(), user__is_staff=True)
        return queryset


class LogEntryAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message')
    list_display = ('__str__', 'action_time', 'user', 'content_type', 'object_link')
    search_fields = ('object_repr', 'change_message')
    list_filter = (UserListFilter, 'content_type')
    list_display_links = None
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return obj is None and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description=_('object'), ordering='object_repr')
    def object_link(self, obj):
        if obj.is_deletion():
            link = obj.object_repr
        else:
            ct = obj.content_type
            try:
                link = format_html('<a href="{1}">{0}</a>', obj.object_repr,
                                   reverse('admin:%s_%s_change' % (ct.app_label, ct.model), args=(obj.object_id,)))
            except NoReverseMatch:
                link = obj.object_repr
        return link

    def queryset(self, request):
        return super().queryset(request).prefetch_related('content_type')
