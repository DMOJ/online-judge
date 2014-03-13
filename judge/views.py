from django.shortcuts import render, render_to_response
from django.contrib.auth.models import User
from django.template import RequestContext
from .models import Profile


def users(request):
    return render_to_response('users.html', {'users': Profile.objects.all()}, context_instance=RequestContext(request))
