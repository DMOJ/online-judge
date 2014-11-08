from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import CreateView

from judge.models import Organization
from judge.utils.ranker import ranker

__all__ = ['organization_list', 'organization_home', 'organization_users', 'join_organization', 'leave_organization',
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
        return render_to_response('generic_message.jade', {
            'message': 'Could not find an organization with the key "%s".' % key,
            'title': 'No such organization'
        }, context_instance=RequestContext(request)), False
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


def organization_home(request, key):
    org, exists = _find_organization(request, key)
    if not exists:
        return org

    return render_to_response('organization.jade', {
        'organization': org,
        'title': org.name,
    }, context_instance=RequestContext(request))


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
    return HttpResponseRedirect(reverse(organization_home, args=(key,)))


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
    return HttpResponseRedirect(reverse(organization_home, args=(key,)))


class NewOrganizationView(CreateView):
    template_name = 'new_organization.jade'
    model = Organization
    fields = ['name', 'key', 'about']

    def form_valid(self, form):
        form.instance.registrant = self.request.user.profile
        return super(NewOrganizationView, self).form_valid(form)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        if self.request.user.profile.points < 50:
            return render_to_response('generic_message.jade', {
                'message': 'You need 50 points to add an organization.',
                'title': "Can't add organization"
            })
        return super(NewOrganizationView, self).dispatch(*args, **kwargs)
