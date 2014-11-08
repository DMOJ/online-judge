from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect, Http404
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, View, UpdateView
from django.views.generic.detail import SingleObjectMixin

from judge.forms import EditOrganizationForm, NewOrganizationForm
from judge.models import Organization
from judge.utils.ranker import ranker
from judge.utils.views import generic_message, TitleMixin, LoginRequiredMixin


__all__ = ['OrganizationList', 'OrganizationHome', 'OrganizationUsers', 'JoinOrganization',
           'LeaveOrganization', 'NewOrganization', 'EditOrganization']


class OrganizationMixin(object):
    context_object_name = 'organization'
    model = Organization
    slug_field = 'key'
    slug_url_kwarg = 'key'

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(OrganizationMixin, self).dispatch(request, *args, **kwargs)
        except Http404:
            key = kwargs.get(self.slug_url_kwarg, None)
            if key:
                return generic_message(request, 'No such organization',
                                       'Could not find an organization with the key "%s".' % key)
            else:
                return generic_message(request, 'No such organization',
                                       'Could not find such organization.')

    def can_edit_organization(self, org=None):
        if org is None:
            org = self.object
        if not self.request.user.is_authenticated():
            return False
        profile_id = self.request.user.profile.id
        return org.admins.filter(id=profile_id).exists() or org.registrant_id == profile_id


class OrganizationList(TitleMixin, ListView):
    model = Organization
    context_object_name = 'organizations'
    template_name = 'organization/list.jade'
    title = 'Organizations'


class OrganizationHome(OrganizationMixin, DetailView):
    template_name = 'organization/home.jade'

    def get_context_data(self, **kwargs):
        context = super(OrganizationHome, self).get_context_data(**kwargs)
        context['title'] = self.object.name
        context['can_edit'] = self.can_edit_organization()
        return context


class OrganizationUsers(OrganizationMixin, DetailView):
    template_name = 'users.jade'

    def get_context_data(self, **kwargs):
        context = super(OrganizationUsers, self).get_context_data(**kwargs)
        context['title'] = '%s Members' % self.object.name
        context['users'] = ranker(self.object.members.filter(points__gt=0, user__is_active=True).order_by('-points'))
        return context


class OrganizationMembershipChange(LoginRequiredMixin, OrganizationMixin, SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        org = self.get_object()
        response = self.handle(request, org, request.user.profile)
        if response is not None:
            return response
        return HttpResponseRedirect(reverse('organization_home', args=(org.key,)))

    def handle(self, request, org, profile):
        raise NotImplementedError()


class JoinOrganization(OrganizationMembershipChange):
    def handle(self, request, org, profile):
        if profile.organization_id is not None:
            return generic_message(request, 'Joining organization', 'You are already in an organization.')
        profile.organization = org
        profile.organization_join_time = timezone.now()
        profile.save()
        cache.delete(make_template_fragment_key('org_member_count', (org.id,)))


class LeaveOrganization(OrganizationMembershipChange):
    def handle(self, request, org, profile):
        if org.id != profile.organization_id:
            return generic_message(request, 'Leaving organization', 'You are not in "%s".' % org.key)
        profile.organization = None
        profile.organization_join_time = None
        profile.save()
        cache.delete(make_template_fragment_key('org_member_count', (org.id,)))


class NewOrganization(LoginRequiredMixin, TitleMixin, CreateView):
    template_name = 'organization/new.jade'
    model = Organization
    form_class = NewOrganizationForm
    title = 'New Organization'

    def form_valid(self, form):
        form.instance.registrant = self.request.user.profile
        return super(NewOrganization, self).form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        profile = request.user.profile
        if profile.points < 50:
            return generic_message(request, "Can't add organization",
                                   'You need 50 points to add an organization.')
        elif profile.organization is not None:
            return generic_message(request, "Can't add organization",
                                   'You are already in an organization.')
        return super(NewOrganization, self).dispatch(request, *args, **kwargs)


class EditOrganization(LoginRequiredMixin, TitleMixin, OrganizationMixin, UpdateView):
    template_name = 'organization/edit.jade'
    model = Organization
    form_class = EditOrganizationForm

    def get_title(self):
        return 'Editing %s' % self.object.name

    def get_object(self, queryset=None):
        object = super(EditOrganization, self).get_object()
        if not self.can_edit_organization(object):
            raise PermissionDenied()
        return object

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(EditOrganization, self).dispatch(request, *args, **kwargs)
        except PermissionDenied:
            return generic_message(request, "Can't edit organization",
                                   'You are not allowed to edit this organization.')
