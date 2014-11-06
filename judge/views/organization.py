from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.forms import ModelForm
from django.http import Http404, HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.comments import problem_comments, comment_form
from judge.forms import ProblemSubmitForm
from judge.models import Problem, Submission, ContestSubmission, ContestProblem, Language, ProblemType, Organization, \
    Profile
from judge.utils.ranker import ranker
from judge.views import user_completed_ids


class OrganizationForm(ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'key', 'about']


def organization_users(request, key):
    try:
        org = Organization.objects.get(key=key)
        return render_to_response('users.jade', {
            'organization': org,
            'title': '%s Members' % org.name,
            'users': ranker(Profile.objects.filter(organization=org, points__gt=0, user__is_active=True).order_by('-points'))
        }, context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return render_to_response('generic_message.jade', {
            'message': 'Could not find an organization with the key "%s".' % key,
            'title': 'No such organization'
        }, context_instance=RequestContext(request))


def organization_home(request, key):
    try:
        org = Organization.objects.get(key=key)
        return render_to_response('organization.jade', {
            'organization': org,
            'title': org.name,
        }, context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return render_to_response('generic_message.jade', {
            'message': 'Could not find an organization with the key "%s".' % key,
            'title': 'No such organization'
        }, context_instance=RequestContext(request))
