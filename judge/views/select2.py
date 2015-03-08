from django.core.paginator import Paginator
from django.db.models import Q
from judge.models import Profile, Organization, Problem

try:
    from django_select2.views import Select2View
except ImportError:
    pass
else:
    class UserSelect2View(Select2View):
        def get_results(self, request, term, page, context):
            queryset = Profile.objects.filter(Q(user__username__icontains=term) | Q(name__icontains=term))\
                              .select_related('user')
            page = Paginator(queryset, 20).page(page)
            return 'nil', page.has_next(), [(user.id, user.long_display_name) for user in page]

    class OrganizationSelect2View(Select2View):
        def get_results(self, request, term, page, context):
            queryset = Organization.objects.filter(Q(key__icontains=term) | Q(name__contains=term))
            page = Paginator(queryset, 20).page(page)
            return 'nil', page.has_next(), [(org.id, org.name) for org in page]

    class ProblemSelect2View(Select2View):
        def get_results(self, request, term, page, context):
            queryset = Problem.objects.filter(Q(code__icontains=term) | Q(name__contains=term))
            if request.user.has_perm('judge.see_private_problem'):
                filter = Q(is_public=True)
                if request.user.is_authenticated():
                    filter |= Q(authors=request.user.profile)
                queryset = queryset.filter(filter)
            page = Paginator(queryset, 20).page(page)
            return 'nil', page.has_next(), [(problem.id, problem.name) for problem in page]