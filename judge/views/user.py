from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.models import Profile


def users(request):
    return render_to_response('users.html', {'users': Profile.objects.all(), 'title': 'Users'},
                              context_instance=RequestContext(request))
