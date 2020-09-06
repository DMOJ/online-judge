from django.forms import ModelForm
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _, ungettext
from reversion.admin import VersionAdmin

from judge.models import Comment
from judge.widgets import AdminHeavySelect2Widget, AdminMartorWidget


class CommentForm(ModelForm):
    class Meta:
        widgets = {
            'author': AdminHeavySelect2Widget(data_view='profile_select2'),
            'parent': AdminHeavySelect2Widget(data_view='comment_select2'),
            'body': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('comment_preview')}),
        }


class CommentAdmin(VersionAdmin):
    fieldsets = (
        (None, {'fields': ('author', 'page', 'parent', 'time', 'score', 'hidden')}),
        ('Content', {'fields': ('body',)}),
    )
    list_display = ['author', 'linked_page', 'time']
    search_fields = ['author__user__username', 'page', 'body']
    actions = ['hide_comment', 'unhide_comment']
    list_filter = ['hidden']
    readonly_fields = ['time']
    actions_on_top = True
    actions_on_bottom = True
    form = CommentForm
    date_hierarchy = 'time'

    def get_queryset(self, request):
        return Comment.objects.order_by('-time')

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

    def linked_page(self, obj):
        link = obj.link
        if link is not None:
            return format_html('<a href="{0}">{1}</a>', link, obj.page)
        else:
            return format_html('{0}', obj.page)
    linked_page.short_description = _('Associated page')
    linked_page.admin_order_field = 'page'

    def save_model(self, request, obj, form, change):
        super(CommentAdmin, self).save_model(request, obj, form, change)
        if obj.hidden:
            obj.get_descendants().update(hidden=obj.hidden)
