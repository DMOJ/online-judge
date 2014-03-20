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
        return render_to_response('user.html', {'user': user, 'title': 'User %s' % user.display_name()},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return Http404()


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
    user_css_class = ["user", "admin"][request.user.is_superuser]
    return render_to_response('users.html', {'users': Profile.objects.all(), 'class': user_css_class, 'title': 'Users'},
                              context_instance=RequestContext(request))
