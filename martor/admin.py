from django.contrib import admin

from .models import MartorField
from .widgets import AdminMartorWidget


class MartorModelAdmin(admin.ModelAdmin):

    formfield_overrides = {
        MartorField: {'widget': AdminMartorWidget},
    }
