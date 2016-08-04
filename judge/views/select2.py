from django.db.models import Q
from django.http import JsonResponse
from django.utils.encoding import smart_text
from django.views.generic.list import BaseListView

from judge.models import Profile, Organization, Problem, Comment, Contest
from judge.templatetags.gravatar import get_gravatar_url


class Select2View(BaseListView):
    paginate_by = 20

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


class ContestSelect2View(Select2View):
    def get_queryset(self):
        queryset = Contest.objects.filter(Q(key__icontains=self.term) | Q(name__icontains=self.term))
        if not self.request.user.has_perm('judge.see_private_contest'):
            queryset = queryset.filter(is_public=True)
        if not self.request.user.has_perm('judge.edit_all_contest'):
            q = Q(is_private=False)
            if self.request.user.is_authenticated():
                q |= Q(organizations__in=self.request.user.profile.organizations.all())
            queryset = queryset.filter(q)
        return queryset


class CommentSelect2View(Select2View):
    def get_queryset(self):
        return Comment.objects.filter(Q(title__icontains=self.term) | Q(page__icontains=self.term))


class UserSearchSelect2View(BaseListView):
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        self.request = request
        self.term = kwargs.get('term', request.GET.get('term', ''))
        self.gravatar_size = request.GET.get('gravatar_size', 128)
        self.gravatar_default = request.GET.get('gravatar_default', None)

        self.object_list = Profile.objects.filter(Q(user__username__icontains=(self.term)) |
                                                  Q(name__icontains=(self.term))).select_related('user')

        context = self.get_context_data()

        return JsonResponse({
            'results': [
                {
                    'text': obj.user.username,
                    'gravatar_url': get_gravatar_url(obj.user.email, self.gravatar_size, self.gravatar_default),
                    'id': obj.pk,
                } for obj in context['object_list']],
            'more': context['page_obj'].has_next(),
        })

    def get_name(self, obj):
        return unicode(obj)
