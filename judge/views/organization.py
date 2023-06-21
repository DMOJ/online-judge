from operator import attrgetter

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.exceptions import PermissionDenied
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.forms import Form, modelformset_factory
from django.http import Http404, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _, gettext_lazy, ngettext
from django.views.generic import DetailView, FormView, ListView, UpdateView, View
from django.views.generic.detail import SingleObjectMixin, SingleObjectTemplateResponseMixin
from reversion import revisions

from judge.forms import EditOrganizationForm
from judge.models import Class, Organization, OrganizationRequest, Profile
from judge.utils.ranker import ranker
from judge.utils.views import DiggPaginatorMixin, QueryStringSortMixin, TitleMixin, generic_message

__all__ = ['OrganizationList', 'OrganizationHome', 'OrganizationUsers', 'OrganizationMembershipChange',
           'JoinOrganization', 'LeaveOrganization', 'EditOrganization', 'RequestJoinOrganization',
           'OrganizationRequestDetail', 'OrganizationRequestView', 'OrganizationRequestLog',
           'KickUserWidgetView', 'ClassHome', 'RequestJoinClass']


def users_for_template(users, order):
    return ranker(users.filter(is_unlisted=False).order_by(order)
                  .select_related('user').defer('about', 'user_script', 'notes'))


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
        return org.admins.filter(id=profile_id).exists()


class BaseOrganizationListView(OrganizationMixin, ListView):
    model = None
    context_object_name = None
    slug_url_kwarg = 'slug'

    def get_object(self):
        return get_object_or_404(Organization, id=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        return super().get_context_data(organization=self.object, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)


class OrganizationDetailView(OrganizationMixin, DetailView):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.slug != kwargs['slug']:
            return HttpResponsePermanentRedirect(reverse(
                request.resolver_match.url_name, args=(self.object.id, self.object.slug)))
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class OrganizationList(TitleMixin, ListView):
    model = Organization
    context_object_name = 'organizations'
    template_name = 'organization/list.html'
    title = gettext_lazy('Organizations')

    def get_queryset(self):
        return super(OrganizationList, self).get_queryset().annotate(member_count=Count('member')).order_by('name')


class OrganizationHome(OrganizationDetailView):
    template_name = 'organization/home.html'

    def get_context_data(self, **kwargs):
        context = super(OrganizationHome, self).get_context_data(**kwargs)
        context['title'] = self.object.name
        context['can_edit'] = self.can_edit_organization()
        context['can_review_requests'] = not self.object.is_open and self.request.user.is_authenticated and (
            self.object.can_review_all_requests(self.request.profile) or
            self.object.can_review_class_requests(self.request.profile)
        )

        classes = self.object.classes.filter(is_active=True)
        if self.request.user.is_authenticated:
            classes = classes.annotate(joined=Subquery(
                self.request.profile.classes.filter(id=OuterRef('id')).values('id'),
            )).order_by('-joined', 'name')
        else:
            classes = classes.annotate(joined=Value(0, output_field=IntegerField()))
        context['classes'] = classes
        return context


class OrganizationUsers(QueryStringSortMixin, DiggPaginatorMixin, BaseOrganizationListView):
    template_name = 'organization/users.html'
    all_sorts = frozenset(('problem_count', 'rating', 'performance_points'))
    default_desc = all_sorts
    default_sort = '-performance_points'
    paginate_by = 100
    context_object_name = 'users'

    def get_queryset(self):
        return self.object.members.filter(is_unlisted=False).order_by(self.order).select_related('user') \
            .defer('about', 'user_script', 'notes')

    def get_context_data(self, **kwargs):
        context = super(OrganizationUsers, self).get_context_data(**kwargs)
        context['title'] = _('%s Members') % self.object.name
        context['users'] = ranker(context['users'])
        context['partial'] = True
        context['is_admin'] = self.can_edit_organization()
        context['kick_url'] = reverse('organization_user_kick', args=[self.object.id, self.object.slug])
        context['first_page_href'] = '.'
        context.update(self.get_sort_context())
        context.update(self.get_sort_paginate_context())
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
                ngettext('You may not be part of more than {count} public organization.',
                         'You may not be part of more than {count} public organizations.',
                         max_orgs).format(count=max_orgs),
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
    class_ = forms.ModelChoiceField(Class.objects.all())
    reason = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, class_required: bool, class_queryset, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['class_'].required = class_required
        self.fields['class_'].queryset = class_queryset
        self.fields['class_'].label_from_instance = attrgetter('name')
        self.show_classes = class_required or bool(class_queryset)


class RequestJoinOrganization(LoginRequiredMixin, SingleObjectMixin, FormView):
    model = Organization
    slug_field = 'key'
    slug_url_kwarg = 'key'
    template_name = 'organization/requests/request.html'
    form_class = OrganizationRequestForm

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.requests.filter(user=self.request.profile, state='P').exists():
            return generic_message(self.request, _("Can't request to join %s") % self.object.name,
                                   _('You already have a pending request to join %s.') % self.object.name)
        if self.object.is_open:
            raise Http404()
        return super(RequestJoinOrganization, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs['class_required'] = self.object.class_required
        kwargs['class_queryset'] = self.object.classes.filter(is_active=True)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(RequestJoinOrganization, self).get_context_data(**kwargs)
        context['title'] = _('Request to join %s') % self.object.name
        return context

    def form_valid(self, form):
        request = OrganizationRequest()
        request.organization = self.get_object()
        request.user = self.request.profile
        request.reason = form.cleaned_data['reason']
        request.request_class = form.cleaned_data['class_']
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
        if object.user_id != profile.id and not object.organization.admins.filter(id=profile.id).exists() and (
                not object.request_class or not object.request_class.admins.filter(id=profile.id).exists()):
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
        if organization.can_review_all_requests(self.request.profile):
            self.edit_all = True
        elif organization.can_review_class_requests(self.request.profile):
            self.edit_all = False
        else:
            raise PermissionDenied()
        return organization

    def get_requests(self):
        queryset = self.object.requests.select_related('user__user').defer(
            'user__about', 'user__notes', 'user__user_script',
        )
        if not self.edit_all:
            queryset = queryset.filter(request_class__in=self.object.classes.filter(admins__id=self.request.profile.id))
        return queryset

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
        self.formset = OrganizationRequestFormSet(queryset=self.get_requests())
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_requests(self):
        return super().get_requests().filter(state='P')

    def post(self, request, *args, **kwargs):
        self.object = organization = self.get_object()
        self.formset = formset = OrganizationRequestFormSet(request.POST, request.FILES, queryset=self.get_requests())
        if formset.is_valid():
            if organization.slots is not None:
                deleted_set = set(formset.deleted_forms)
                to_approve = sum(form.cleaned_data['state'] == 'A' for form in formset.forms if form not in deleted_set)
                can_add = organization.slots - organization.members.count()
                if to_approve > can_add:
                    msg1 = ngettext('Your organization can only receive %d more member.',
                                    'Your organization can only receive %d more members.', can_add) % can_add
                    msg2 = ngettext('You cannot approve %d user.',
                                    'You cannot approve %d users.', to_approve) % to_approve
                    messages.error(request, msg1 + '\n' + msg2)
                    return self.render_to_response(self.get_context_data(object=organization))

            approved, rejected = 0, 0
            for obj in formset.save():
                if obj.state == 'A':
                    obj.user.organizations.add(obj.organization)
                    if obj.request_class:
                        obj.user.classes.add(obj.request_class)
                    approved += 1
                elif obj.state == 'R':
                    rejected += 1
            messages.success(request,
                             ngettext('Approved %d user.', 'Approved %d users.', approved) % approved + '\n' +
                             ngettext('Rejected %d user.', 'Rejected %d users.', rejected) % rejected)
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
        context['requests'] = self.get_requests().filter(state__in=self.states)
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
        with revisions.create_revision(atomic=True):
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
                                   _('The user you are trying to kick is not in organization: %s') %
                                   organization.name, status=400)

        organization.members.remove(user)
        return HttpResponseRedirect(organization.get_users_url())


class ClassMixin(TitleMixin, SingleObjectTemplateResponseMixin, SingleObjectMixin):
    context_object_name = 'class'
    model = Class
    pk_url_kwarg = 'cpk'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        org = self.object.organization
        if self.object.slug != kwargs['cslug'] or org.id != kwargs['pk'] or org.slug != kwargs['slug']:
            return HttpResponsePermanentRedirect(self.object.get_absolute_url())
        context = self.get_context_data()
        return self.render_to_response(context)


class ClassHome(QueryStringSortMixin, ClassMixin, DetailView):
    template_name = 'organization/class.html'
    all_sorts = frozenset(('problem_count', 'rating', 'performance_points'))
    default_desc = all_sorts
    default_sort = '-performance_points'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['logo_override_image'] = self.object.organization.logo_override_image
        context['users'] = users_for_template(self.object.members, self.order)
        context['is_admin'] = False  # Don't allow kicking here
        context.update(self.get_sort_context())
        return context

    def get_content_title(self):
        org = self.object.organization
        return mark_safe(escape(_('Class {name} in {organization}')).format(
            name=escape(self.object.name),
            organization=format_html('<a href="{0}">{1}</a>', org.get_absolute_url(), org.name),
        ))

    def get_title(self):
        return _('Class {name} - {organization}').format(
            name=self.object.name, organization=self.object.organization.name,
        )


class ClassRequestForm(Form):
    reason = forms.CharField(widget=forms.Textarea)


class RequestJoinClass(LoginRequiredMixin, ClassMixin, FormView):
    template_name = 'organization/requests/request.html'
    form_class = ClassRequestForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        self.object = self.get_object()
        org = self.object.organization
        if not org.members.filter(id=self.request.profile.id).exists():
            return HttpResponseRedirect(reverse('request_organization', args=(org.id, org.slug)))
        if org.requests.filter(user=self.request.profile, state='P', request_class=self.object).exists():
            return generic_message(self.request, _("Can't request to join %s") % self.object.name,
                                   _('You already have a pending request to join %s.') % self.object.name)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Request to join {name} in {organization}').format(
            name=self.object.name, organization=self.object.organization.name,
        )
        return context

    def form_valid(self, form):
        request = OrganizationRequest()
        request.organization = self.object.organization
        request.user = self.request.profile
        request.reason = form.cleaned_data['reason']
        request.request_class = self.object
        request.state = 'P'
        request.save()
        return HttpResponseRedirect(reverse('request_organization_detail', args=(
            request.organization.id, request.organization.slug, request.id,
        )))
