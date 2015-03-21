from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Max, Count
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.html import format_html
from django.views.generic import DetailView
import reversion

from judge.forms import ProfileForm
from judge.models import Profile, Submission
from judge.utils.ranker import ranker
from .contests import contest_ranking_view
from judge.utils.views import TitleMixin

__all__ = ['user', 'edit_profile', 'UserRating']


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
            'authored': user.authored_problems.filter(is_public=True).order_by('code'),
            'title': 'My Account' if request.user == user.user else 'User %s' % user.long_display_name,
        },  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return render_to_response('generic_message.jade', {
            'message': 'No user handle "%s".' % user,
            'title': 'No such user'
        }, context_instance=RequestContext(request))


@login_required
def edit_profile(request):
    profile = Profile.objects.get(user=request.user)
    if profile.mute:
        raise Http404()
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            with transaction.atomic(), reversion.create_revision():
                form.save()
                reversion.set_user(request.user)
                reversion.set_comment('Updated on site')
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
                               .annotate(problems=Count('submission__problem', distinct=True)).order_by('-points')
                               .select_related('user__username', 'organization').defer('about', 'organization__about')),
        'title': 'Users'
    }, context_instance=RequestContext(request))


class UserRating(TitleMixin, DetailView):
    model = Profile
    slug_url_kwarg = 'username'
    slug_field = 'user__username'
    template_name = 'user/rating.jade'

    def get_title(self):
        return 'Rating history for %s' % self.object.long_display_name

    def get_content_title(self):
        return format_html(u'Rating history for <span class="{1}"><a href="{2}">{0}</a></span>',
                           self.object.long_display_name, self.object.display_rank,
                           reverse('judge.views.user', args=[self.object.user.username]))

    def get_context_data(self, **kwargs):
        context = super(UserRating, self).get_context_data(**kwargs)
        context['ratings'] = self.object.ratings.all()
        return context
