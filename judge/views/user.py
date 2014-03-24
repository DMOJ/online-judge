from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.forms import ProfileForm
from judge.models import Profile


def user(request, user):
    try:
        user = Profile.objects.get(user__username=user)
        return render_to_response('user.html', {'user': user, 'title': 'User %s' % user.long_display_name()},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        raise Http404()


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
    return render_to_response('edit_profile.html', {'form': form, 'title': 'Edit profile'},
                              context_instance=RequestContext(request))


def users(request):
    return render_to_response('users.html', {'users': sorted(Profile.objects.all(), key=lambda x: x.get_points()), 'title': 'Users'},
                              context_instance=RequestContext(request))
