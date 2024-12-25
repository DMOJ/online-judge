from django import forms

from .settings import MARTOR_ENABLE_LABEL
from .widgets import (MartorWidget, AdminMartorWidget)


class MartorFormField(forms.CharField):

    def __init__(self, *args, **kwargs):

        # to setup the editor without label
        if not MARTOR_ENABLE_LABEL:
            kwargs['label'] = ''

        super(MartorFormField, self).__init__(*args, **kwargs)

        if not issubclass(self.widget.__class__, MartorWidget):
            self.widget = MartorWidget()
