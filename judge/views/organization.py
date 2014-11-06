from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.forms import ModelForm
from django.http import Http404, HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.comments import problem_comments, comment_form
from judge.forms import ProblemSubmitForm
from judge.models import Problem, Submission, ContestSubmission, ContestProblem, Language, ProblemType, Organization
from judge.views import user_completed_ids

class ProfileForm(ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'key', 'about']
