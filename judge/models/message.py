from django.db import models
from django.db.models import CASCADE
from django.utils.translation import gettext_lazy as _

from judge.models.profile import Profile

__all__ = ['PrivateMessage', 'PrivateMessageThread']


class PrivateMessage(models.Model):
    title = models.CharField(verbose_name=_('message title'), max_length=50)
    content = models.TextField(verbose_name=_('message body'))
    sender = models.ForeignKey(Profile, verbose_name=_('sender'), related_name='sent_messages', on_delete=CASCADE)
    target = models.ForeignKey(Profile, verbose_name=_('target'), related_name='received_messages', on_delete=CASCADE)
    timestamp = models.DateTimeField(verbose_name=_('message timestamp'), auto_now_add=True)
    read = models.BooleanField(verbose_name=_('read'), default=False)


class PrivateMessageThread(models.Model):
    messages = models.ManyToManyField(PrivateMessage, verbose_name=_('messages in the thread'))
