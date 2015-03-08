from django.core.paginator import Paginator
from django.db.models import Q
from judge.models import Profile

try:
    from django_select2.views import Select2View
except ImportError:
    pass
else:
    class UserSelect2View(Select2View):
        def get_results(self, request, term, page, context):
            queryset = Profile.objects.filter(Q(user__username__contains=term, name__contains=term))\
                              .select_related('user')
            page = Paginator(queryset, 20).page(page)
            return 'nil', page.has_next(), [(user.id, user.long_display_name) for user in page]