from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.forms import Form, modelformset_factory
from django.http import Http404, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext as _, gettext_lazy, ungettext
from django.views.generic import DetailView, FormView, ListView, UpdateView, View
from django.views.generic.detail import SingleObjectMixin, SingleObjectTemplateResponseMixin
from reversion import revisions

from judge.forms import EditOrganizationForm
from judge.models import Organization, OrganizationRequest, Profile
from judge.utils.ranker import ranker
from judge.utils.views import TitleMixin, generic_message

__all__ = ['OrganizationList', 'OrganizationHome', 'OrganizationUsers', 'OrganizationMembershipChange',
           'JoinOrganization', 'LeaveOrganization', 'EditOrganization', 'RequestJoinOrganization',
           'OrganizationRequestDetail', 'OrganizationRequestView', 'OrganizationRequestLog',
           'KickUserWidgetView']


class OrganizationMixin(object):
    context_object_name = 'organization'
    model = Organization

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['logo_override_image'] = self.object.logo_override_image
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(OrganizationMixin, self).dispatch(request, *args, **kwargs)
        except Http404:
            key = kwargs.get(self.slug_url_kwarg, None)
            if key:
                return generic_message(request, _('No such organization'),
                                       _('Could not find an organization with the key "%s".') % key)
            else:
                return generic_message(request, _('No such organization'),
                                       _('Could not find such organization.'))

    def can_edit_organization(self, org=None):
        if org is None:
            org = self.object
        if not self.request.user.is_authenticated:
            return False
        profile_id = self.request.profile.id
        return org.admins.filter(id=profile_id).exists() or org.registrant_id == profile_id


class OrganizationDetailView(OrganizationMixin, DetailView):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.slug != kwargs['slug']:
            return HttpResponsePermanentRedirect(reverse('organization_home', args=(self.object.id, self.object.slug)))
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class OrganizationList(TitleMixin, ListView):
    model = Organization
    context_object_name = 'organizations'
    template_name = 'organization/list.html'
    title = gettext_lazy('Organizations')

    def get_queryset(self):
        return super(OrganizationList, self).get_queryset().annotate(member_count=Count('member'))


class OrganizationHome(OrganizationDetailView):
    template_name = 'organization/home.html'

    def get_context_data(self, **kwargs):
        context = super(OrganizationHome, self).get_context_data(**kwargs)
        context['title'] = self.object.name
        context['can_edit'] = self.can_edit_organization()
        return context


class OrganizationUsers(OrganizationDetailView):
    template_name = 'organization/users.html'

    def get_context_data(self, **kwargs):
        context = super(OrganizationUsers, self).get_context_data(**kwargs)
        context['title'] = _('%s Members') % self.object.name
        context['users'] = \
            ranker(self.object.members.filter(is_unlisted=False).order_by('-performance_points', '-problem_count')
                   .select_related('user').defer('about', 'user_script', 'notes'))
        context['partial'] = True
        context['is_admin'] = self.can_edit_organization()
        context['kick_url'] = reverse('organization_user_kick', args=[self.object.id, self.object.slug])
        return context


class OrganizationMembershipChange(LoginRequiredMixin, OrganizationMixin, SingleObjectMixin, View):
    def post(self, request, *args, **kwargs):
        org = self.get_object()
        response = self.handle(request, org, request.profile)
        if response is not None:
            return response
        return HttpResponseRedirect(org.get_absolute_url())

    def handle(self, request, org, profile):
        raise NotImplementedError()


class JoinOrganization(OrganizationMembershipChange):
    def handle(self, request, org, profile):
        if profile.organizations.filter(id=org.id).exists():
            return generic_message(request, _('Joining organization'), _('You are already in the organization.'))

        if not org.is_open:
            return generic_message(request, _('Joining organization'), _('This organization is not open.'))

        max_orgs = settings.DMOJ_USER_MAX_ORGANIZATION_COUNT
        if profile.organizations.filter(is_open=True).count() >= max_orgs:
            return generic_message(
                request, _('Joining organization'),
                _('You may not be part of more than {count} public organizations.').format(count=max_orgs),
            )

        profile.organizations.add(org)
        profile.save()
        cache.delete(make_template_fragment_key('org_member_count', (org.id,)))


class LeaveOrganization(OrganizationMembershipChange):
    def handle(self, request, org, profile):
        if not profile.organizations.filter(id=org.id).exists():
            return generic_message(request, _('Leaving organization'), _('You are not in "%s".') % org.short_name)
        profile.organizations.remove(org)
        cache.delete(make_template_fragment_key('org_member_count', (org.id,)))


class OrganizationRequestForm(Form):
    reason = forms.CharField(widget=forms.Textarea)


class RequestJoinOrganization(LoginRequiredMixin, SingleObjectMixin, FormView):
    model = Organization
    slug_field = 'key'
    slug_url_kwarg = 'key'
    template_name = 'organization/requests/request.html'
    form_class = OrganizationRequestForm

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(RequestJoinOrganization, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RequestJoinOrganization, self).get_context_data(**kwargs)
        if self.object.is_open:
            raise Http404()
        context['title'] = _('Request to join %s') % self.object.name
        return context

    def form_valid(self, form):
        request = OrganizationRequest()
        request.organization = self.get_object()
        request.user = self.request.profile
        request.reason = form.cleaned_data['reason']
        request.state = 'P'
        request.save()
        return HttpResponseRedirect(reverse('request_organization_detail', args=(
            request.organization.id, request.organization.slug, request.id,
        )))


class OrganizationRequestDetail(LoginRequiredMixin, TitleMixin, DetailView):
    model = OrganizationRequest
    template_name = 'organization/requests/detail.html'
    title = gettext_lazy('Join request detail')
    pk_url_kwarg = 'rpk'

    def get_object(self, queryset=None):
        object = super(OrganizationRequestDetail, self).get_object(queryset)
        profile = self.request.profile
        if object.user_id != profile.id and not object.organization.admins.filter(id=profile.id).exists():
            raise PermissionDenied()
        return object


OrganizationRequestFormSet = modelformset_factory(OrganizationRequest, extra=0, fields=('state',), can_delete=True)


class OrganizationRequestBaseView(LoginRequiredMixin, SingleObjectTemplateResponseMixin, SingleObjectMixin, View):
    model = Organization
    slug_field = 'key'
    slug_url_kwarg = 'key'
    tab = None

    def get_object(self, queryset=None):
        organization = super(OrganizationRequestBaseView, self).get_object(queryset)
        if not (organization.admins.filter(id=self.request.profile.id).exists() or
                organization.registrant_id == self.request.profile.id):
            raise PermissionDenied()
        return organization

    def get_context_data(self, **kwargs):
        context = super(OrganizationRequestBaseView, self).get_context_data(**kwargs)
        context['title'] = _('Managing join requests for %s') % self.object.name
        context['tab'] = self.tab
        return context


class OrganizationRequestView(OrganizationRequestBaseView):
    template_name = 'organization/requests/pending.html'
    tab = 'pending'

    def get_context_data(self, **kwargs):
        context = super(OrganizationRequestView, self).get_context_data(**kwargs)
        context['formset'] = self.formset
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.formset = OrganizationRequestFormSet(
            queryset=OrganizationRequest.objects.filter(state='P', organization=self.object),
        )
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = organization = self.get_object()
        self.formset = formset = OrganizationRequestFormSet(request.POST, request.FILES)
        if formset.is_valid():
            if organization.slots is not None:
                deleted_set = set(formset.deleted_forms)
                to_approve = sum(form.cleaned_data['state'] == 'A' for form in formset.forms if form not in deleted_set)
                can_add = organization.slots - organization.members.count()
                if to_approve > can_add:
                    messages.error(request, _('Your organization can only receive %d more members. '
                                              'You cannot approve %d users.') % (can_add, to_approve))
                    return self.render_to_response(self.get_context_data(object=organization))

            approved, rejected = 0, 0
            for obj in formset.save():
                if obj.state == 'A':
                    obj.user.organizations.add(obj.organization)
                    approved += 1
                elif obj.state == 'R':
                    rejected += 1
            messages.success(request,
                             ungettext('Approved %d user.', 'Approved %d users.', approved) % approved + '\n' +
                             ungettext('Rejected %d user.', 'Rejected %d users.', rejected) % rejected)
            cache.delete(make_template_fragment_key('org_member_count', (organization.id,)))
            return HttpResponseRedirect(request.get_full_path())
        return self.render_to_response(self.get_context_data(object=organization))

    put = post


class OrganizationRequestLog(OrganizationRequestBaseView):
    states = ('A', 'R')
    tab = 'log'
    template_name = 'organization/requests/log.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(OrganizationRequestLog, self).get_context_data(**kwargs)
        context['requests'] = self.object.requests.filter(state__in=self.states)
        return context


class EditOrganization(LoginRequiredMixin, TitleMixin, OrganizationMixin, UpdateView):
    template_name = 'organization/edit.html'
    model = Organization
    form_class = EditOrganizationForm

    def get_title(self):
        return _('Editing %s') % self.object.name

    def get_object(self, queryset=None):
        object = super(EditOrganization, self).get_object()
        if not self.can_edit_organization(object):
            raise PermissionDenied()
        return object

    def get_form(self, form_class=None):
        form = super(EditOrganization, self).get_form(form_class)
        form.fields['admins'].queryset = \
            Profile.objects.filter(Q(organizations=self.object) | Q(admin_of=self.object)).distinct()
        return form

    def form_valid(self, form):
        with transaction.atomic(), revisions.create_revision():
            revisions.set_comment(_('Edited from site'))
            revisions.set_user(self.request.user)
            return super(EditOrganization, self).form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(EditOrganization, self).dispatch(request, *args, **kwargs)
        except PermissionDenied:
            return generic_message(request, _("Can't edit organization"),
                                   _('You are not allowed to edit this organization.'), status=403)


class KickUserWidgetView(LoginRequiredMixin, OrganizationMixin, SingleObjectMixin, View):
    def post(self, request, *args, **kwargs):
        organization = self.get_object()
        if not self.can_edit_organization(organization):
            return generic_message(request, _("Can't edit organization"),
                                   _('You are not allowed to kick people from this organization.'), status=403)

        try:
            user = Profile.objects.get(id=request.POST.get('user', None))
        except Profile.DoesNotExist:
            return generic_message(request, _("Can't kick user"),
                                   _('The user you are trying to kick does not exist!'), status=400)

        if not organization.members.filter(id=user.id).exists():
            return generic_message(request, _("Can't kick user"),
                                   _('The user you are trying to kick is not in organization: %s.') %
                                   organization.name, status=400)

        organization.members.remove(user)
        return HttpResponseRedirect(organization.get_users_url())
