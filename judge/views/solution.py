from django.http import Http404
from django.utils import timezone
from django.views.generic import DetailView
from judge.models import Solution


class SolutionView(DetailView):
    model = Solution
    slug_field = slug_url_kwarg = 'url'
    template_name = 'flatpages/dmsolutions.jade'
    context_object_name = 'flatpage'

    def get_object(self, queryset=None):
        solution = super(SolutionView, self).get_object(queryset)
        if (not solution.is_public or solution.publish_on > timezone.now()) and \
                not self.request.user.has_perm('judge.see_private_solution'):
            raise Http404()
        return solution
