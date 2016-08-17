from django.http import HttpResponseBadRequest
from django.views.generic import TemplateView


class MarkdownPreviewView(TemplateView):
    def get(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)

    def _allowed_methods(self):
        return ['POST']

    def post(self, request, *args, **kwargs):
        try:
            self.preview_data = data = request.POST['preview']
        except KeyError:
            return HttpResponseBadRequest('No preview data specified.')

        return self.render_to_response(self.get_context_data(
            preview_data=data,
        ))


class ProblemMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'problem/preview.jade'
