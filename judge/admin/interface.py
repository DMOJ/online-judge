from django.contrib import admin
from django.core.urlresolvers import reverse_lazy, reverse
from django.forms import ModelForm
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _, ugettext
from mptt.admin import MPTTModelAdmin
from reversion.admin import VersionAdmin

from judge.dblock import LockModel
from judge.models import NavigationBar
from judge.widgets import HeavySelect2MultipleWidget, HeavyPreviewAdminPageDownWidget, HeavySelect2Widget


class NavigationBarAdmin(MPTTModelAdmin):
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
    def __init__(self, *args, **kwargs):
        super(SolutionForm, self).__init__(*args, **kwargs)
        self.fields['authors'].widget.can_add_related = False

    class Meta:
        widgets = {
            'authors': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
            'problem': HeavySelect2Widget(data_view='problem_select2', attrs={'style': 'width: 250px'}),
        }

        if HeavyPreviewAdminPageDownWidget is not None:
            widgets['content'] = HeavyPreviewAdminPageDownWidget(preview=reverse_lazy('solution_preview'))


class SolutionAdmin(VersionAdmin):
    fields = ('title', 'is_public', 'publish_on', 'problem', 'authors', 'content')
    list_display = ('title', 'problem_link', 'show_public')
    search_fields = ('title', 'problem__name', 'problem__code')
    form = SolutionForm

    def show_public(self, obj):
        return format_html(u'<a href="{0}" style="white-space:nowrap;">{1}</a>',
                           obj.get_absolute_url(), ugettext('View on site'))
    show_public.short_description = ''

    def problem_link(self, obj):
        if obj.problem is None:
            return 'N/A'
        return format_html(u'<a href="{}">{}</a>', reverse('admin:judge_problem_change', args=[obj.problem_id]),
                           obj.problem.name)
    problem_link.short_description = _('Problem')
    problem_link.admin_order_field = 'problem__name'


class LicenseForm(ModelForm):
    class Meta:
        if HeavyPreviewAdminPageDownWidget is not None:
            widgets = {'text': HeavyPreviewAdminPageDownWidget(preview=reverse_lazy('license_preview'))}


class LicenseAdmin(admin.ModelAdmin):
    fields = ('key', 'link', 'name', 'display', 'icon', 'text')
    list_display = ('name', 'key')
    form = LicenseForm
