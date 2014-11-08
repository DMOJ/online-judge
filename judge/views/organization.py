from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView

from judge.models import Organization
from judge.utils.ranker import ranker
from judge.utils.views import generic_message


__all__ = ['organization_list', 'OrganizationHomeView', 'organization_users', 'join_organization', 'leave_organization',
           'NewOrganizationView']


def organization_list(request):
    return render_to_response('organizations.jade', {
        'organizations': Organization.objects.all(),
        'title': 'Organizations'
    }, context_instance=RequestContext(request))


def _find_organization(request, key):
    try:
        organization = Organization.objects.get(key=key)
    except ObjectDoesNotExist:
        return generic_message(request, 'No such organization',
                               'Could not find an organization with the key "%s".' % key), False
    return organization, True


def organization_users(request, key):
    org, exists = _find_organization(request, key)
    if not exists:
        return org

    return render_to_response('users.jade', {
        'organization': org,
        'title': '%s Members' % org.name,
        'users': ranker(org.members.filter(points__gt=0, user__is_active=True).order_by('-points'))
    }, context_instance=RequestContext(request))


def organization_not_found(request, key):
    if key:
        return generic_message(request, 'No such organization',
                               'Could not find an organization with the key "%s".' % key)
    else:
        return generic_message(request, 'No such organization',
                               'Could not find such organization.')


class OrganizationHomeView(DetailView):
    context_object_name = 'organization'
    model = Organization
    slug_field = 'key'
    slug_url_kwarg = 'key'
    template_name = 'organization.jade'

    def get_context_data(self, **kwargs):
        context = super(OrganizationHomeView, self).get_context_data(**kwargs)
        context['title'] = self.object.name
        return context

    def get(self, request, *args, **kwargs):
        try:
            return super(OrganizationHomeView, self).get(self, request, *args, **kwargs)
        except Http404:
            return organization_not_found(request, kwargs.get(self.slug_url_kwarg, None))


@login_required
def join_organization(request, key):
    org, exists = _find_organization(request, key)
    if not exists:
        return org

    profile = request.user.profile
    if profile.organization_id is not None:
        return render_to_response('generic_message.jade', {
            'message': 'You are already in an organization.' % key,
            'title': 'Joining organization'
        }, context_instance=RequestContext(request))

    profile.organization = org
    profile.organization_join_time = timezone.now()
    profile.save()
    cache.delete(make_template_fragment_key('org_member_count', (org.id,)))
    return HttpResponseRedirect(reverse('organization_home', args=(key,)))


@login_required
def leave_organization(request, key):
    org, exists = _find_organization(request, key)
    if not exists:
        return org

    profile = request.user.profile
    if org.id != profile.organization_id:
        return render_to_response('generic_message.jade', {
            'message': 'You are not in "%s".' % key,
            'title': 'Leaving organization'
        }, context_instance=RequestContext(request))
    profile.organization = None
    profile.organization_join_time = None
    profile.save()
    cache.delete(make_template_fragment_key('org_member_count', (org.id,)))
    return HttpResponseRedirect(reverse('organization_home', args=(key,)))


class NewOrganizationView(CreateView):
    template_name = 'new_organization.jade'
    model = Organization
    fields = ['name', 'key', 'about']

    def form_valid(self, form):
        form.instance.registrant = self.request.user.profile
        return super(NewOrganizationView, self).form_valid(form)

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        profile = request.user.profile
        if profile.points < 50:
            return generic_message(request, "Can't add organization",
                                   'You need 50 points to add an organization.')
        elif profile.organization is not None:
            return generic_message(request, "Can't add organization",
                                   'You are already in an organization.')
        return super(NewOrganizationView, self).dispatch(request, *args, **kwargs)
