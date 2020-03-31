from django.http import HttpResponseBadRequest
from django.views.generic.base import ContextMixin, TemplateResponseMixin, View


class MarkdownPreviewView(TemplateResponseMixin, ContextMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            self.preview_data = data = request.POST['content']
        except KeyError:
            return HttpResponseBadRequest('No preview data specified.')

        return self.render_to_response(self.get_context_data(
            preview_data=data,
        ))


class ProblemMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'problem/preview.html'


class BlogMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'blog/preview.html'


class ContestMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'contest/preview.html'


class CommentMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'comments/preview.html'


class FlatPageMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'flatpage-preview.html'


class ProfileMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'user/preview.html'


class OrganizationMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'organization/preview.html'


class SolutionMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'solution-preview.html'


class LicenseMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'license-preview.html'


class TicketMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'ticket/preview.html'


class DefaultMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'default-preview.html'
