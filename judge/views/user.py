from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max, Count
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from judge.forms import ProfileForm
from judge.models import Profile, Submission
from judge.utils.ranker import ranker
from .contests import contest_ranking_view


def remap_keys(iterable, mapping):
    return [dict((mapping.get(k, k), v) for k, v in item.iteritems()) for item in iterable]


def user(request, user=None):
    try:
        if user is None:
            if not request.user.is_authenticated():
                return redirect_to_login(request.get_full_path())
            user = request.user.profile
        else:
            user = Profile.objects.select_related('user').get(user__username=user)
        result = Submission.objects.filter(user=user, points__gt=0, problem__is_public=True) \
            .values('problem__code', 'problem__name', 'problem__points', 'problem__group__full_name') \
            .distinct().annotate(points=Max('points')).order_by('problem__group__full_name', 'problem__name')
        result = remap_keys(result, {
            'problem__code': 'code', 'problem__name': 'name', 'problem__points': 'total',
            'problem__group__full_name': 'group'
        })
        return render_to_response('user/user.jade', {
            'user': user, 'best_submissions': result,
            'title': 'My Account' if request.user == user.user else 'User %s' % user.long_display_name,
        },  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return render_to_response('generic_message.jade', {'message': 'No user handle "%s".' % user,
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
    return render_to_response('user/edit_profile.jade', {'form': form, 'title': 'Edit profile'},
                              context_instance=RequestContext(request))


def users(request):
    if request.user.is_authenticated() and request.user.profile.contest.current is not None:
        return contest_ranking_view(request, request.user.profile.contest.current.contest)
    return render_to_response('user/list.jade', {
        'users': ranker(Profile.objects.filter(points__gt=0, user__is_active=True, submission__points__gt=0)
                               .annotate(problems=Count('submission__problem', distinct=True)).order_by('-points')),
        'title': 'Users'
    }, context_instance=RequestContext(request))
