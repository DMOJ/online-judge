from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.utils.encoding import smart_text
from django.views.generic.list import BaseListView

from judge.models import Profile, Organization, Problem, Comment, ContestProfile


class Select2View(BaseListView):
    def get(self, request, *args, **kwargs):
        self.request = request
        self.term = kwargs.get('term', request.GET.get('term', ''))
        self.object_list = self.get_queryset()
        context = self.get_context_data()

        return JsonResponse({
            'results': [
                {
                    'text': smart_text(self.get_name(obj)),
                    'id': obj.pk,
                } for obj in context['object_list']],
            'more': context['page_obj'].has_next(),
        })

    def get_name(self, obj):
        return unicode(obj)


class UserSelect2View(Select2View):
    def get_queryset(self):
        return Profile.objects.filter(Q(user__username__icontains=(self.term)) | Q(name__icontains=(self.term))) \
            .select_related('user')


class OrganizationSelect2View(Select2View):
    def get_queryset(self):
        return Organization.objects.filter(Q(key__icontains=self.term) | Q(name__icontains=self.term))


class ProblemSelect2View(Select2View):
    def get_queryset(self):
        queryset = Problem.objects.filter(Q(code__icontains=self.term) | Q(name__icontains=self.term))
        if not self.request.user.has_perm('judge.see_private_problem'):
            filter = Q(is_public=True)
            if self.request.user.is_authenticated():
                filter |= Q(authors=self.request.user.profile)
            queryset = queryset.filter(filter)
        return queryset


class CommentSelect2View(Select2View):
    def get_queryset(self):
        return Comment.objects.filter(Q(title__icontains=self.term) | Q(page__icontains=self.term))


class ContestProfileSelect2View(Select2View):
    def get_queryset(self):
        if not self.request.user.has_perm('judge.change_contestparticipation'):
            raise PermissionDenied()
        return ContestProfile.objects.filter(
            Q(user__user__username__icontains=self.term) | Q(user__name__icontains=self.term)) \
            .select_related('user__user')
