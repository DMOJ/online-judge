from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from judge.forms import ProfileForm
from judge.models import Profile, Submission


def user(request, user=None):
    try:
        if user is None:
            if not request.user.is_authenticated():
                return redirect_to_login(request.get_full_path())
            user = request.user.profile
        else:
            user = Profile.objects.select_related('user').get(user__username=user)
        result = Submission.objects.filter(user=user, points__gt=0) \
            .values('problem__code', 'problem__name', 'problem__points', 'problem__group__full_name') \
            .distinct().annotate(points=Max('points')).order_by('problem__group__full_name', 'problem__name')
        return render_to_response('user.jade', {'user': user, 
                                                'title': 'My Account' if request.user == user.user else 'User %s' % user.long_display_name,
                                                'best_submissions': result},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return render_to_response('message.jade', {'message': 'No user handle "%s".' % user,
                                                   'title': 'No such user'},
                                  context_instance=RequestContext(request))


@login_required
def edit_profile(request):
    profile = Profile.objects.get(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.path)
    else:
        form = ProfileForm(instance=profile)
    return render_to_response('edit_profile.jade', {'form': form, 'title': 'Edit profile'},
                              context_instance=RequestContext(request))


def ranker(profiles):
    rank = 0
    delta = 1
    last = -1
    for profile in profiles:
        if profile.points != last:
            rank += delta
            delta = 0
        delta += 1
        yield rank, profile
        last = round(profile.points, 1)


def users(request):
    return render_to_response('users.jade', {
        'users': ranker(Profile.objects.filter(points__gt=0).order_by('-points')),
        'title': 'Users'
    }, context_instance=RequestContext(request))
