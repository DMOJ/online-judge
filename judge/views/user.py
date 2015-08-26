import django
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Max, Count, Min
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.template import RequestContext, Context
from django.utils.html import format_html
from django.views.generic import DetailView
import reversion

from judge.forms import ProfileForm
from judge.models import Profile, Submission, Rating
from judge.utils.ranker import ranker
from .contests import contest_ranking_view
from judge.utils.views import TitleMixin, generic_message

__all__ = ['UserPage', 'users', 'edit_profile', 'UserRating']


def remap_keys(iterable, mapping):
    return [dict((mapping.get(k, k), v) for k, v in item.iteritems()) for item in iterable]


class UserMixin(object):
    model = Profile
    slug_field = 'user__username'
    slug_url_kwarg = 'username'
    context_object_name = 'user'

    def render_to_response(self, context, **response_kwargs):
        if django.VERSION < (1, 8) and not isinstance(context, Context):
            context = RequestContext(self.request, context)
            context[self.context_object_name] = self.object
        return super(UserMixin, self).render_to_response(context, **response_kwargs)


class UserPage(TitleMixin, UserMixin, DetailView):
    template_name = 'user/user.jade'

    def get_object(self, queryset=None):
        if self.kwargs.get(self.slug_url_kwarg, None) is None:
            return self.request.user.profile
        return super(UserPage, self).get_object(queryset)

    def dispatch(self, request, *args, **kwargs):
        if self.kwargs.get(self.slug_url_kwarg, None) is None:
            if not self.request.user.is_authenticated():
                return redirect_to_login(self.request.get_full_path())
        try:
            return super(UserPage, self).dispatch(request, *args, **kwargs)
        except Http404:
            return generic_message(request, 'No such user', 'No user handle "%s".' %
                                   self.kwargs.get(self.slug_url_kwarg, None))

    def get_title(self):
        return 'My Account' if self.request.user == self.object.user else 'User %s' % self.object.long_display_name

    def get_context_data(self, **kwargs):
        context = super(UserPage, self).get_context_data(**kwargs)

        result = Submission.objects.filter(user=self.object, points__gt=0, problem__is_public=True) \
            .values('problem__code', 'problem__name', 'problem__points', 'problem__group__full_name') \
            .distinct().annotate(points=Max('points')).order_by('problem__group__full_name', 'problem__name')
        context['best_submissions'] = remap_keys(result, {
            'problem__code': 'code', 'problem__name': 'name', 'problem__points': 'total',
            'problem__group__full_name': 'group'
        })
        context['authored'] = self.object.authored_problems.filter(is_public=True).order_by('code')
        rating = self.object.ratings.order_by('-contest__end_time')[:1]
        context['rating'] = rating[0] if rating else None
        context['rank'] = Profile.objects.filter(points__gt=self.object.points).count() + 1
        context['users'] = Profile.objects.filter(points__gt=0).count()
        if rating:
            context['rating_rank'] = Profile.objects.filter(rating__gt=self.object.rating).count() + 1
            context['rated_users'] = Profile.objects.filter(rating__isnull=False).count()
        context.update(self.object.ratings.aggregate(min_rating=Min('rating'), max_rating=Max('rating'),
                                                     contests=Count('contest')))
        return context


@login_required
def edit_profile(request):
    profile = Profile.objects.get(user=request.user)
    if profile.mute:
        raise Http404()
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            with transaction.atomic(), reversion.create_revision():
                form.save()
                reversion.set_user(request.user)
                reversion.set_comment('Updated on site')
            return HttpResponseRedirect(request.path)
    else:
        form = ProfileForm(instance=profile, user=request.user)
    tzmap = getattr(settings, 'TIMEZONE_MAP', None)
    return render(request, 'user/edit_profile.jade', {
        'form': form, 'title': 'Edit profile',
        'TIMEZONE_MAP': tzmap or 'http://momentjs.com/static/img/world.png',
        'TIMEZONE_BG': getattr(settings, 'TIMEZONE_BG', None if tzmap else '#4E7CAD'),
    })


def users(request):
    if request.user.is_authenticated() and request.user.profile.contest.current is not None:
        return contest_ranking_view(request, request.user.profile.contest.current.contest)
    return render(request, 'user/list.jade', {
        'users': ranker(Profile.objects.filter(points__gt=0, user__is_active=True, submission__points__gt=0)
                               .annotate(problems=Count('submission__problem', distinct=True)).order_by('-points')
                               .select_related('user__username')
                               .only('display_rank', 'user__username', 'name', 'points', 'rating')),
        'title': 'Users'
    })


class UserRating(TitleMixin, UserMixin, DetailView):
    template_name = 'user/rating.jade'

    def get_title(self):
        return 'Rating history for %s' % self.object.long_display_name

    def get_content_title(self):
        return format_html(u'Rating history for <span class="{1}"><a href="{2}">{0}</a></span>',
                           self.object.user.username, self.object.display_rank,
                           reverse('user_page', args=[self.object.user.username]))

    def get_context_data(self, **kwargs):
        context = super(UserRating, self).get_context_data(**kwargs)
        ratings = context['ratings'] = self.object.ratings.order_by('-contest__end_time').select_related('contest') \
                                           .defer('contest__description')
        if ratings:
            user_data = self.object.ratings.aggregate(Min('rating'), Max('rating'))
            global_data = Rating.objects.aggregate(Min('rating'), Max('rating'))
            min_ever, max_ever = global_data['rating__min'], global_data['rating__max']
            min_user, max_user = user_data['rating__min'], user_data['rating__max']
            delta = max_user - min_user
            ratio = (max_ever - max_user + 0.0) / (max_ever - min_ever)
            context['max_graph'] = max_user + ratio * delta
            context['min_graph'] = min_user + ratio * delta - delta
        return context
