from django.contrib import admin
from django.db import models

from .widgets import AdminMartorWidget
from .models import MartorField


class MartorModelAdmin(admin.ModelAdmin):

    formfield_overrides = {
        MartorField: {'widget': AdminMartorWidget}
    }
