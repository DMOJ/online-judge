from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from judge.tasks.polygon import parce_task_from_polygon
from judge.template_context import get_profile
from judge.utils.views import TitleMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.contrib.auth.mixins import PermissionRequiredMixin

class NewProblemFromCFView(PermissionRequiredMixin, TitleMixin, TemplateView):
    permission_required = 'judge.add_problem'
    template_name = 'problem/data_from_cf.html'
    title = 'New problem from polygon'
    
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        return super().get(self, request, *args, **kwargs)
    
    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        problem_code = request.POST.get('problem_code')
        polygon_link = request.POST.get('polygon_link')
        
        profile_id = get_profile(request).id
        parce_task_from_polygon.delay(problem_code, polygon_link, profile_id)
        # parce_task_from_polygon(problem_code, polygon_link, profile_id)

        return HttpResponseRedirect(f"/problem/{problem_code}/test_data")
    
