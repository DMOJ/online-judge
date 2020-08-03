from django.db import models

from judge.models import Profile


class PEGUser(models.Model):
    user = models.OneToOneField(Profile, related_name='peg_user', on_delete=models.PROTECT)
    merge_into = models.OneToOneField(Profile, related_name='peg_merge_into', null=True, on_delete=models.PROTECT)
