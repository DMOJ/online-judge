from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.models import Contest

__all__ = ['contest_list']


def contest_list(request):
    if request.user.is_authenticated() and request.profile.is_admin:
        contests = Contest.objects.all()
    else:
        contests = Contest.objects.filter(is_public=True)
    return render_to_response('contests.jade', {
        'contests': contests,
        'title': 'Contests'
    }, context_instance=RequestContext(request))
