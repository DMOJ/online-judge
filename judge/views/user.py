import json
from datetime import datetime

import django
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Max, Count, Min
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404
from django.template import RequestContext, Context
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _, ugettext_lazy
from django.views.generic import DetailView, ListView
from reversion import revisions

from judge.forms import ProfileForm, newsletter_id
from judge.models import Profile, Submission, Rating
from judge.ratings import rating_class, rating_progress
from judge.utils.problems import contest_completed_ids, user_completed_ids
from judge.utils.ranker import ranker
from judge.utils.subscription import Subscription
from judge.utils.views import TitleMixin, generic_message, LoadSelect2Mixin, DiggPaginatorMixin
from .contests import contest_ranking_view

__all__ = ['UserPage', 'UserAboutPage', 'UserProblemsPage', 'users', 'edit_profile']


def remap_keys(iterable, mapping):
    return [dict((mapping.get(k, k), v) for k, v in item.iteritems()) for item in iterable]


class UserMixin(object):
    model = Profile
    slug_field = 'user__username'
    slug_url_kwarg = 'user'
    context_object_name = 'user'

    def render_to_response(self, context, **response_kwargs):
        if django.VERSION < (1, 8) and not isinstance(context, Context):
            context = RequestContext(self.request, context)
            context[self.context_object_name] = self.object
        return super(UserMixin, self).render_to_response(context, **response_kwargs)


class UserPage(TitleMixin, UserMixin, DetailView):
    template_name = 'user/user_base.jade'

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
            return generic_message(request, _('No such user'), _('No user handle "%s".') %
                                   self.kwargs.get(self.slug_url_kwarg, None))

    def get_title(self):
        return (_('My Account') if self.request.user == self.object.user else
                _('User %s') % self.object.long_display_name)

    # TODO: the same code exists in problem.py, maybe move to problems.py?
    @cached_property
    def profile(self):
        if not self.request.user.is_authenticated():
            return None
        return self.request.user.profile

    @cached_property
    def in_contest(self):
        return self.profile is not None and self.profile.current_contest is not None

    def get_completed_problems(self):
        if self.in_contest:
            return contest_completed_ids(self.profile.current_contest)
        else:
            return user_completed_ids(self.profile) if self.profile is not None else ()

    def get_context_data(self, **kwargs):
        context = super(UserPage, self).get_context_data(**kwargs)

        context['hide_solved'] = int(self.hide_solved)
        result = Submission.objects.filter(user=self.object, points__gt=0, problem__is_public=True) \
            .exclude(problem__id__in=self.get_completed_problems() if self.hide_solved else []) \
            .values('problem__id', 'problem__code', 'problem__name', 'problem__points', 'problem__group__full_name') \
            .distinct().annotate(points=Max('points')).order_by('problem__group__full_name', 'problem__code')
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

    def get(self, request, *args, **kwargs):
        self.hide_solved = request.GET.get('hide_solved') == '1' if 'hide_solved' in request.GET else False
        return super(UserPage, self).get(request, *args, **kwargs)


EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class UserAboutPage(UserPage):
    template_name = 'user/user_about.jade'

    def get_context_data(self, **kwargs):
        context = super(UserAboutPage, self).get_context_data(**kwargs)
        ratings = context['ratings'] = self.object.ratings.order_by('-contest__end_time').select_related('contest') \
            .defer('contest__description')

        context['rating_data'] = mark_safe(json.dumps([
                                                          {'label': rating.contest.name, 'rating': rating.rating,
                                                           'ranking': rating.rank,
                                                           'link': reverse('contest_ranking',
                                                                           args=(rating.contest.key,)),
                                                           'timestamp': (
                                                                            rating.contest.end_time - EPOCH).total_seconds() * 1000,
                                                           'date': date_format(rating.contest.end_time,
                                                                               _('M j, Y, G:i')),
                                                           'class': rating_class(rating.rating),
                                                           'height': '%.3fem' % rating_progress(rating.rating)}
                                                          for rating in ratings
                                                          ]))

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


class UserProblemsPage(UserPage):
    template_name = 'user/user_problems.jade'


@login_required
def edit_profile(request):
    profile = Profile.objects.get(user=request.user)
    if profile.mute:
        raise Http404()
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            with transaction.atomic(), revisions.create_revision():
                form.save()
                revisions.set_user(request.user)
                revisions.set_comment(_('Updated on site'))

            if newsletter_id is not None:
                try:
                    subscription = Subscription.objects.get(user=request.user, newsletter_id=newsletter_id)
                except Subscription.DoesNotExist:
                    if form.cleaned_data['newsletter']:
                        Subscription(user=request.user, newsletter_id=newsletter_id, subscribed=True).save()
                else:
                    if subscription.subscribed != form.cleaned_data['newsletter']:
                        subscription.update(('unsubscribe', 'subscribe')[form.cleaned_data['newsletter']])

            return HttpResponseRedirect(request.path)
    else:
        form = ProfileForm(instance=profile, user=request.user)
        if newsletter_id is not None:
            try:
                subscription = Subscription.objects.get(user=request.user, newsletter_id=newsletter_id)
            except Subscription.DoesNotExist:
                form.fields['newsletter'].initial = False
            else:
                form.fields['newsletter'].initial = subscription.subscribed

    tzmap = getattr(settings, 'TIMEZONE_MAP', None)
    return render(request, 'user/edit_profile.jade', {
        'form': form, 'title': _('Edit profile'),
        'TIMEZONE_MAP': tzmap or 'http://momentjs.com/static/img/world.png',
        'TIMEZONE_BG': getattr(settings, 'TIMEZONE_BG', None if tzmap else '#4E7CAD'),
    })


class UserList(LoadSelect2Mixin, DiggPaginatorMixin, TitleMixin, ListView):
    model = Profile
    title = ugettext_lazy('Leaderboard')
    context_object_name = 'users'
    template_name = 'user/list.jade'
    paginate_by = 100

    def get_queryset(self):
        return (Profile.objects.filter(points__gt=0, user__is_active=True)
                .order_by('-points', 'id').select_related('user__username')
                .only('display_rank', 'user__username', 'name', 'points', 'rating'))

    def get_context_data(self, **kwargs):
        context = super(UserList, self).get_context_data(**kwargs)
        context['users'] = ranker(context['users'], rank=self.paginate_by * (context['page_obj'].number - 1))
        context['first_page_href'] = '.'

        return context


user_list_view = UserList.as_view()


def users(request):
    if request.user.is_authenticated():
        participation = request.user.profile.current_contest
        if participation is not None:
            return contest_ranking_view(request, participation.contest, participation)
    return user_list_view(request)


def user_ranking_redirect(request):
    try:
        username = request.GET['handle']
    except KeyError:
        raise Http404()
    user = get_object_or_404(Profile, user__username=username)
    rank = Profile.objects.filter(points__gt=user.points, user__is_active=True).count()
    rank += Profile.objects.filter(points__exact=user.points, id__lt=user.id, user__is_active=True).count()
    page = rank // UserList.paginate_by
    return HttpResponseRedirect('%s#!%s' % (reverse('user_list', args=[page + 1] if page else []), username))
