from django.contrib.admin import ModelAdmin
from django.contrib.admin.options import InlineModelAdmin

from judge.models import TicketMessage


class TicketMessageInline(InlineModelAdmin):
    model = TicketMessage


class TicketAdmin(ModelAdmin):
    fields = ('title', 'user', 'time', 'assignees', 'content_type', 'object_id', 'notes')
    list_display = ('title', 'user', 'time', 'linked_item')
    inlines = [TicketMessageInline]
