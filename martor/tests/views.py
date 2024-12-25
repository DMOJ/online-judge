
from django.views.generic.edit import CreateView

from .models import Post


class TestFormView(CreateView):
    template_name = 'test_form_view.html'
    model = Post
    fields = ['description', 'wiki']
