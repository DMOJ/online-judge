from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.models import Profile


def user(request, user):
    print request.path
    try:
        user = Profile.objects.get(user__username=user)
        return render_to_response('user.html', {'user': user, 'title': 'User %s' % user.display_name()},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return Http404()


def users(request):
    return render_to_response('users.html', {'users': Profile.objects.all(), 'title': 'Users'},
                              context_instance=RequestContext(request))
