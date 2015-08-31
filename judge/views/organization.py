from itertools import chain
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Count, Max
from django.http import HttpResponseRedirect, Http404
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, View, UpdateView
from django.views.generic.detail import SingleObjectMixin
import reversion

from judge.forms import EditOrganizationForm, NewOrganizationForm
from judge.models import Organization
from judge.utils.ranker import ranker
from judge.utils.views import generic_message, TitleMixin, LoginRequiredMixin


__all__ = ['OrganizationList', 'OrganizationHome', 'OrganizationUsers', 'JoinOrganization',
           'LeaveOrganization', 'EditOrganization']


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
    template_name = 'user/list.jade'

    def get_context_data(self, **kwargs):
        context = super(OrganizationUsers, self).get_context_data(**kwargs)
        context['title'] = '%s Members' % self.object.name
        context['users'] = ranker(chain(*[
            i.select_related('user__username').defer('about') for i in (
                self.object.members.filter(submission__points__gt=0).order_by('-points')
                    .annotate(problems=Count('submission__problem', distinct=True)),
                self.object.members.annotate(problems=Max('submission__points')).filter(problems=0),
                self.object.members.annotate(problems=Count('submission__problem', distinct=True)).filter(problems=0),
            )
        ]))
        context['partial'] = True
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
        if profile.organizations.filter(id=org.id).exists():
            return generic_message(request, 'Joining organization', 'You are already in the organization.')
        if not org.is_open:
            return generic_message(request, 'Joining organization', 'This organization is not open.')
        profile.organizations.add(org)
        profile.save()
        cache.delete(make_template_fragment_key('org_member_count', (org.id,)))


class LeaveOrganization(OrganizationMembershipChange):
    def handle(self, request, org, profile):
        if not profile.organizations.filter(id=org.id).exists():
            return generic_message(request, 'Leaving organization', 'You are not in "%s".' % org.key)
        profile.organizations.remove(org)
        cache.delete(make_template_fragment_key('org_member_count', (org.id,)))


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

    def form_valid(self, form):
        with transaction.atomic(), reversion.create_revision():
            reversion.set_comment('Edited from site')
            reversion.set_user(self.request.user)
            return super(EditOrganization, self).form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(EditOrganization, self).dispatch(request, *args, **kwargs)
        except PermissionDenied:
            return generic_message(request, "Can't edit organization",
                                   'You are not allowed to edit this organization.')
