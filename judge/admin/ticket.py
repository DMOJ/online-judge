from django.contrib.admin import ModelAdmin
from django.contrib.admin.options import StackedInline
from django.forms import ModelForm
from django.urls import reverse_lazy

from judge.models import TicketMessage
from judge.widgets import HeavySelect2Widget, HeavySelect2MultipleWidget, HeavyPreviewAdminPageDownWidget


class TicketMessageForm(ModelForm):
    class Meta:
        widgets = {
            'user': HeavySelect2Widget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
        }
        if HeavyPreviewAdminPageDownWidget is not None:
            widgets['body'] = HeavyPreviewAdminPageDownWidget(preview=reverse_lazy('ticket_preview'))


class TicketMessageInline(StackedInline):
    model = TicketMessage
    form = TicketMessageForm
    fields = ('user', 'body')


class TicketForm(ModelForm):
    class Meta:
        widgets = {
            'user': HeavySelect2Widget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
            'assignees': HeavySelect2MultipleWidget(data_view='profile_select2', attrs={'style': 'width: 100%'}),
        }


class TicketAdmin(ModelAdmin):
    fields = ('title', 'time', 'user', 'assignees', 'content_type', 'object_id', 'notes')
    readonly_fields = ('time',)
    list_display = ('title', 'user', 'time', 'linked_item')
    inlines = [TicketMessageInline]
    form = TicketForm
    date_hierarchy = 'time'
