
from django.db import models

from martor.models import MartorField


class Post(models.Model):
    description = MartorField()
    wiki = MartorField()

    class Meta:
        app_label = 'Post'
