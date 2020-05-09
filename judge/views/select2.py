from django.db.models import F, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.encoding import smart_text
from django.views.generic.list import BaseListView

from judge.jinja2.gravatar import gravatar
from judge.models import Comment, Contest, Organization, Problem, Profile


def _get_user_queryset(term):
    qs = Profile.objects
    if term.endswith(' '):
        qs = qs.filter(user__username=term.strip())
    else:
        qs = qs.filter(user__username__icontains=term)
    return qs


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
        return str(obj)


class UserSelect2View(Select2View):
    def get_queryset(self):
        return _get_user_queryset(self.term).annotate(username=F('user__username')).only('id')

    def get_name(self, obj):
        return obj.username


class OrganizationSelect2View(Select2View):
    def get_queryset(self):
        return Organization.objects.filter(name__icontains=self.term)


class ProblemSelect2View(Select2View):
    def get_queryset(self):
        return Problem.get_visible_problems(self.request.user) \
                      .filter(Q(code__icontains=self.term) | Q(name__icontains=self.term)).distinct()


class ContestSelect2View(Select2View):
    def get_queryset(self):
        return Contest.get_visible_contests(self.request.user) \
                      .filter(Q(key__icontains=self.term) | Q(name__icontains=self.term))


class CommentSelect2View(Select2View):
    def get_queryset(self):
        return Comment.objects.filter(page__icontains=self.term)


class UserSearchSelect2View(BaseListView):
    paginate_by = 20

    def get_queryset(self):
        return _get_user_queryset(self.term)

    def get(self, request, *args, **kwargs):
        self.request = request
        self.kwargs = kwargs
        self.term = kwargs.get('term', request.GET.get('term', ''))
        self.gravatar_size = request.GET.get('gravatar_size', 128)
        self.gravatar_default = request.GET.get('gravatar_default', None)

        self.object_list = self.get_queryset().values_list('pk', 'user__username', 'user__email', 'display_rank')

        context = self.get_context_data()

        return JsonResponse({
            'results': [
                {
                    'text': username,
                    'id': username,
                    'gravatar_url': gravatar(email, self.gravatar_size, self.gravatar_default),
                    'display_rank': display_rank,
                } for pk, username, email, display_rank in context['object_list']],
            'more': context['page_obj'].has_next(),
        })

    def get_name(self, obj):
        return str(obj)


class ContestUserSearchSelect2View(UserSearchSelect2View):
    def get_queryset(self):
        contest = get_object_or_404(Contest, key=self.kwargs['contest'])
        if not contest.is_accessible_by(self.request.user) or not contest.can_see_full_scoreboard(self.request.user):
            raise Http404()

        return Profile.objects.filter(contest_history__contest=contest,
                                      user__username__icontains=self.term).distinct()


class TicketUserSelect2View(UserSearchSelect2View):
    def get_queryset(self):
        return Profile.objects.filter(tickets__isnull=False,
                                      user__username__icontains=self.term).distinct()


class AssigneeSelect2View(UserSearchSelect2View):
    def get_queryset(self):
        return Profile.objects.filter(assigned_tickets__isnull=False,
                                      user__username__icontains=self.term).distinct()
