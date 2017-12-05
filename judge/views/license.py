from django.views.generic import DetailView

from judge.models import License
from judge.utils.views import TitleMixin


class LicenseDetail(TitleMixin, DetailView):
    model = License
    slug_field = slug_url_kwarg = 'key'
    context_object_name = 'license'
    template_name = 'license.html'

    def get_title(self):
        return self.object.name
