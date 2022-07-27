from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from judge.models.profile import Profile


class Ticket(models.Model):
    title = models.CharField(max_length=100, verbose_name=_('ticket title'))
    user = models.ForeignKey(Profile, verbose_name=_('ticket creator'), related_name='tickets',
                             on_delete=models.CASCADE)
    time = models.DateTimeField(verbose_name=_('creation time'), auto_now_add=True)
    assignees = models.ManyToManyField(Profile, verbose_name=_('assignees'), related_name='assigned_tickets',
                                       blank=True)
    notes = models.TextField(verbose_name=_('quick notes'), blank=True,
                             help_text=_('Staff notes for this issue to aid in processing.'))
    content_type = models.ForeignKey(ContentType, verbose_name=_('linked item type'),
                                     on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(verbose_name=_('linked item ID'))
    linked_item = GenericForeignKey()
    is_open = models.BooleanField(verbose_name=_('is ticket open?'), default=True)

    class Meta:
        verbose_name = _('ticket')
        verbose_name_plural = _('tickets')


class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, verbose_name=_('ticket'), related_name='messages',
                               related_query_name='message', on_delete=models.CASCADE)
    user = models.ForeignKey(Profile, verbose_name=_('user'), related_name='ticket_messages',
                             on_delete=models.CASCADE)
    body = models.TextField(verbose_name=_('message body'))
    time = models.DateTimeField(verbose_name=_('message time'), auto_now_add=True)

    class Meta:
        verbose_name = _('ticket message')
        verbose_name_plural = _('ticket messages')
