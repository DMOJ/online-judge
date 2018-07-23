from calendar import Calendar, SUNDAY
from collections import namedtuple, defaultdict
from functools import partial
from itertools import chain
from operator import attrgetter

from datetime import timedelta, date, datetime, time
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import connection, IntegrityError
from django.db.models import Q, Min, Max, Count, Sum, Case, When, IntegerField
from django.http import HttpResponseRedirect, HttpResponseBadRequest, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import escape, format_html
from django.utils.timezone import make_aware
from django.utils.translation import ugettext as _, ugettext_lazy
from django.views.generic import ListView, TemplateView
from django.views.generic.detail import BaseDetailView, DetailView

from judge import event_poster as event
from judge.comments import CommentedDetailView
from judge.models import Contest, ContestParticipation, ContestTag, Profile
from judge.models import Problem
from judge.timezone import from_database_time
from judge.utils.opengraph import generate_opengraph
from judge.utils.ranker import ranker
from judge.utils.views import TitleMixin, generic_message

__all__ = ['ContestList', 'ContestDetail', 'contest_ranking', 'ContestJoin', 'ContestLeave', 'ContestCalendar',
           'contest_ranking_ajax', 'participation_list', 'own_participation_list', 'get_contest_ranking_list',
           'base_contest_ranking_list']


def _find_contest(request, key, private_check=True):
    try:
        contest = Contest.objects.get(key=key)
        if private_check and not contest.is_public and not request.user.has_perm('judge.see_private_contest') and (
                    not request.user.has_perm('judge.edit_own_contest') or
                    not contest.organizers.filter(id=request.user.profile.id).exists()):
            raise ObjectDoesNotExist()
    except ObjectDoesNotExist:
        return generic_message(request, _('No such contest'),
                               _('Could not find a contest with the key "%s".') % key, status=404), False
    return contest, True


class ContestListMixin(object):
    def get_queryset(self):
        queryset = Contest.objects.all()
        if not self.request.user.has_perm('judge.see_private_contest'):
            q = Q(is_public=True)
            if self.request.user.is_authenticated:
                q |= Q(organizers=self.request.user.profile)
            queryset = queryset.filter(q)
        if not self.request.user.has_perm('judge.edit_all_contest'):
            q = Q(is_private=False)
            if self.request.user.is_authenticated:
                q |= Q(organizations__in=self.request.user.profile.organizations.all())
            queryset = queryset.filter(q)
        return queryset.distinct()


class ContestList(TitleMixin, ContestListMixin, ListView):
    model = Contest
    template_name = 'contest/list.html'
    title = ugettext_lazy('Contests')

    def get_queryset(self):
        return super(ContestList, self).get_queryset() \
            .order_by('-start_time', 'key').prefetch_related('tags')

    def get_context_data(self, **kwargs):
        context = super(ContestList, self).get_context_data(**kwargs)
        now = timezone.now()
        past, present, future = [], [], []
        for contest in self.get_queryset():
            if contest.end_time < now:
                past.append(contest)
            elif contest.start_time > now:
                future.append(contest)
            else:
                present.append(contest)
        future.sort(key=attrgetter('start_time'))
        context['current_contests'] = present
        context['past_contests'] = past
        context['future_contests'] = future
        context['now'] = timezone.now()
        return context


class PrivateContestError(Exception):
    def __init__(self, name, orgs):
        self.name = name
        self.orgs = orgs


class ContestMixin(object):
    context_object_name = 'contest'
    model = Contest
    slug_field = 'key'
    slug_url_kwarg = 'contest'

    @cached_property
    def is_organizer(self):
        return self.check_organizer()

    def check_organizer(self, contest=None, profile=None):
        if profile is None:
            if not self.request.user.is_authenticated:
                return False
            profile = self.request.user.profile
        return (contest or self.object).organizers.filter(id=profile.id).exists()

    def get_context_data(self, **kwargs):
        context = super(ContestMixin, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            profile = self.request.user.profile
            in_contest = context['in_contest'] = (profile.current_contest is not None and
                                                  profile.current_contest.contest == self.object)
            if in_contest:
                context['participation'] = profile.current_contest
                context['participating'] = True
            else:
                try:
                    context['participation'] = profile.contest_history.get(contest=self.object, virtual=0)
                except ContestParticipation.DoesNotExist:
                    context['participating'] = False
                    context['participation'] = None
                else:
                    context['participating'] = True
        else:
            context['participating'] = False
            context['participation'] = None
            context['in_contest'] = False
        context['now'] = timezone.now()
        context['is_organizer'] = self.is_organizer

        if not self.object.og_image or not self.object.summary:
            metadata = generate_opengraph('generated-meta-contest:%d' % self.object.id,
                                          self.object.description, 'contest')
        context['meta_description'] = self.object.summary or metadata[0]
        context['og_image'] = self.object.og_image or metadata[1]

        return context

    def get_object(self, queryset=None):
        contest = super(ContestMixin, self).get_object(queryset)
        user = self.request.user
        profile = self.request.user.profile if user.is_authenticated else None

        if (profile is not None and
                ContestParticipation.objects.filter(id=profile.current_contest_id, contest_id=contest.id).exists()):
            return contest

        if not contest.is_public and not user.has_perm('judge.see_private_contest') and (
                    not user.has_perm('judge.edit_own_contest') or
                    not self.check_organizer(contest, profile)):
            raise Http404()

        if contest.is_private:
            if profile is None or (not user.has_perm('judge.edit_all_contest') and
                                       not contest.organizations.filter(id__in=profile.organizations.all()).exists()):
                raise PrivateContestError(contest.name, contest.organizations.all())
        return contest

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(ContestMixin, self).dispatch(request, *args, **kwargs)
        except Http404:
            key = kwargs.get(self.slug_url_kwarg, None)
            if key:
                return generic_message(request, _('No such contest'),
                                       _('Could not find a contest with the key "%s".') % key)
            else:
                return generic_message(request, _('No such contest'),
                                       _('Could not find such contest.'))
        except PrivateContestError as e:
            return render(request, 'contest/private.html', {
                'orgs': e.orgs, 'title': _('Access to contest "%s" denied') % escape(e.name)
            }, status=403)


class ContestDetail(ContestMixin, TitleMixin, CommentedDetailView):
    template_name = 'contest/contest.html'

    def get_comment_page(self):
        return 'c:%s' % self.object.key

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super(ContestDetail, self).get_context_data(**kwargs)
        context['contest_problems'] = Problem.objects.filter(contests__contest=self.object) \
            .order_by('contests__order').defer('description') \
            .annotate(has_public_editorial=Sum(Case(When(solution__is_public=True, then=1),
                                                    default=0, output_field=IntegerField()))) \
            .add_i18n_name(self.request.LANGUAGE_CODE)
        return context


class ContestAccessDenied(Exception):
    pass


class ContestAccessCodeForm(forms.Form):
    access_code = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super(ContestAccessCodeForm, self).__init__(*args, **kwargs)
        self.fields['access_code'].widget.attrs.update({'autocomplete': 'off'})


class ContestJoin(LoginRequiredMixin, ContestMixin, BaseDetailView):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return self.join_contest(request)
        except ContestAccessDenied:
            return self.ask_for_access_code()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.ask_for_access_code(ContestAccessCodeForm(request.POST))

    def join_contest(self, request, access_code=None):
        contest = self.object

        if not contest.can_join and not self.is_organizer:
            return generic_message(request, _('Contest not ongoing'),
                                   _('"%s" is not currently ongoing.') % contest.name)

        profile = request.user.profile
        if profile.current_contest is not None:
            return generic_message(request, _('Already in contest'),
                                   _('You are already in a contest: "%s".') % profile.current_contest.contest.name)

        if contest.ended:
            while True:
                virtual_id = (ContestParticipation.objects.filter(contest=contest, user=profile)
                              .aggregate(virtual_id=Max('virtual'))['virtual_id'] or 0) + 1
                try:
                    participation = ContestParticipation.objects.create(
                        contest=contest, user=profile, virtual=virtual_id,
                        real_start=timezone.now()
                    )
                # There is obviously a race condition here, so we keep trying until we win the race.
                except IntegrityError:
                    pass
                else:
                    break
        else:
            try:
                participation = ContestParticipation.objects.get(
                    contest=contest, user=profile, virtual=(-1 if self.is_organizer else 0)
                )
            except ContestParticipation.DoesNotExist:
                if contest.access_code and access_code != contest.access_code:
                    raise ContestAccessDenied()

                participation = ContestParticipation.objects.create(
                    contest=contest, user=profile, virtual=(-1 if self.is_organizer else 0),
                    real_start=timezone.now(),
                )
            else:
                if participation.ended:
                    participation = ContestParticipation.objects.get_or_create(
                        contest=contest, user=profile, virtual=-1,
                        defaults={
                            'real_start': timezone.now()
                        }
                    )[0]

        profile.current_contest = participation
        profile.save()
        contest._updating_stats_only = True
        contest.update_user_count()
        return HttpResponseRedirect(reverse('problem_list'))

    def ask_for_access_code(self, form=None):
        contest = self.object
        wrong_code = False
        if form:
            if form.is_valid():
                if form.cleaned_data['access_code'] == contest.access_code:
                    return self.join_contest(self.request, form.cleaned_data['access_code'])
                wrong_code = True
        else:
            form = ContestAccessCodeForm()
        return render(self.request, 'contest/access_code.html', {
            'form': form, 'wrong_code': wrong_code,
            'title': _('Enter access code for "%s"') % contest.name,
        })


class ContestLeave(LoginRequiredMixin, ContestMixin, BaseDetailView):
    def get(self, request, *args, **kwargs):
        contest = self.get_object()

        profile = request.user.profile
        if profile.current_contest is None or profile.current_contest.contest_id != contest.id:
            return generic_message(request, _('No such contest'),
                                   _('You are not in contest "%s".') % contest.key, 404)

        profile.remove_contest()
        return HttpResponseRedirect(reverse('contest_view', args=(contest.key,)))


ContestDay = namedtuple('ContestDay', 'date weekday is_pad is_today starts ends oneday')


class ContestCalendar(TitleMixin, ContestListMixin, TemplateView):
    firstweekday = SUNDAY
    weekday_classes = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
    template_name = 'contest/calendar.html'
    title = ugettext_lazy('Contests')

    def get(self, request, *args, **kwargs):
        try:
            self.year = int(kwargs['year'])
            self.month = int(kwargs['month'])
        except (KeyError, ValueError):
            raise ImproperlyConfigured(_('ContestCalender requires integer year and month'))
        self.today = timezone.now().date()
        return self.render()

    def render(self):
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_contest_data(self, start, end):
        end += timedelta(days=1)
        contests = self.get_queryset().filter(Q(start_time__gte=start, start_time__lt=end) |
                                              Q(end_time__gte=start, end_time__lt=end)).defer('description')
        starts, ends, oneday = (defaultdict(list) for i in xrange(3))
        for contest in contests:
            start_date = timezone.localtime(contest.start_time).date()
            end_date = timezone.localtime(contest.end_time).date()
            if start_date == end_date:
                oneday[start_date].append(contest)
            else:
                starts[start_date].append(contest)
                ends[end_date].append(contest)
        return starts, ends, oneday

    def get_table(self):
        calendar = Calendar(self.firstweekday).monthdatescalendar(self.year, self.month)
        starts, ends, oneday = self.get_contest_data(make_aware(datetime.combine(calendar[0][0], time.min)),
                                                     make_aware(datetime.combine(calendar[-1][-1], time.min)))
        return [[ContestDay(
            date=date, weekday=self.weekday_classes[weekday], is_pad=date.month != self.month,
            is_today=date == self.today, starts=starts[date], ends=ends[date], oneday=oneday[date],
        ) for weekday, date in enumerate(week)] for week in calendar]

    def get_context_data(self, **kwargs):
        context = super(ContestCalendar, self).get_context_data(**kwargs)

        try:
            context['month'] = date(self.year, self.month, 1)
        except ValueError:
            raise Http404()

        dates = Contest.objects.aggregate(min=Min('start_time'), max=Max('end_time'))
        min_month = (self.today.year, self.today.month)
        if dates['min'] is not None:
            min_month = dates['min'].year, dates['min'].month
        max_month = (self.today.year, self.today.month)
        if dates['max'] is not None:
            max_month = max((dates['max'].year, dates['max'].month), (self.today.year, self.today.month))


        month = (self.year, self.month)
        if month < min_month or month > max_month:
            # 404 is valid because it merely declares the lack of existence, without any reason
            raise Http404()

        context['now'] = timezone.now()
        context['calendar'] = self.get_table()

        if month > min_month:
            context['prev_month'] = date(self.year - (self.month == 1), 12 if self.month == 1 else self.month - 1, 1)
        else:
            context['prev_month'] = None

        if month < max_month:
            context['next_month'] = date(self.year + (self.month == 12), 1 if self.month == 12 else self.month + 1, 1)
        else:
            context['next_month'] = None
        return context


class CachedContestCalendar(ContestCalendar):
    def render(self):
        key = 'contest_cal:%d:%d' % (self.year, self.month)
        cached = cache.get(key)
        if cached is not None:
            return HttpResponse(cached)
        response = super(CachedContestCalendar, self).render()
        response.render()
        cached.set(key, response.content)
        return response


class ContestRankingProfile(namedtuple(
    'ContestRankingProfile', 'id user display_rank long_display_name points cumtime problems rating organization '
                             'participation participation_rating')):
    @cached_property
    def css_class(self):
        return Profile.get_user_css_class(self.display_rank, self.rating)


BestSolutionData = namedtuple('BestSolutionData', 'code points time state is_pretested')


def make_contest_ranking_profile(participation, problems):
    user = participation.user
    return ContestRankingProfile(
        id=user.id,
        user=user.user,
        display_rank=user.display_rank,
        long_display_name=user.long_display_name,
        points=participation.score,
        cumtime=participation.cumtime,
        organization=user.organization,
        rating=user.rating,
        participation_rating=participation.rating.rating if hasattr(participation, 'rating') else None,
        problems=problems,
        participation=participation,
    )


def best_solution_state(points, total):
    if not points:
        return 'failed-score'
    if points == total:
        return 'full-score'
    return 'partial-score'


def base_contest_ranking_list(contest, problems, queryset, for_user=None):
    cursor = connection.cursor()
    cursor.execute('''
        SELECT part.id, cp.id, prob.code, MAX(cs.points) AS best, MAX(sub.date) AS `last`
        FROM judge_contestproblem cp CROSS JOIN judge_contestparticipation part INNER JOIN
             judge_problem prob ON (cp.problem_id = prob.id) LEFT OUTER JOIN
             judge_contestsubmission cs ON (cs.problem_id = cp.id AND cs.participation_id = part.id) LEFT OUTER JOIN
             judge_submission sub ON (sub.id = cs.submission_id)
        WHERE cp.contest_id = %s AND part.contest_id = %s {extra}
        GROUP BY cp.id, part.id
    '''.format(extra=('AND part.user_id = %s' if for_user is not None else
                                         'AND part.virtual = 0')),
                   (contest.id, contest.id) + ((for_user,) if for_user is not None else ()))
    data = {(part, prob): (code, best, last and from_database_time(last)) for part, prob, code, best, last in cursor}
    cursor.close()

    problems = map(attrgetter('id', 'points', 'is_pretested'), problems)

    def make_ranking_profile(participation):
        part = participation.id
        return make_contest_ranking_profile(participation, [
            BestSolutionData(code=data[part, prob][0], points=data[part, prob][1],
                             time=data[part, prob][2] - participation.start,
                             state=best_solution_state(data[part, prob][1], points),
                             is_pretested=is_pretested)
            if (part, prob) in data and data[part, prob][1] is not None else None
            for prob, points, is_pretested in problems])

    return map(make_ranking_profile, queryset.select_related('user__user', 'rating')
               .defer('user__about', 'user__organizations__about'))


def contest_ranking_list(contest, problems):
    return base_contest_ranking_list(contest, problems, contest.users.filter(virtual=0)
                                                                     .prefetch_related('user__organizations')
                                                                     .order_by('-score', 'cumtime'))


def get_participation_ranking_profile(contest, participation, problems):
    scoring = {data['id']: (data['score'], data['time']) for data in
               contest.contest_problems.filter(submission__participation=participation)
                   .annotate(score=Max('submission__points'), time=Max('submission__submission__date'))
                   .values('score', 'time', 'id')}

    return make_contest_ranking_profile(participation, [
        BestSolutionData(code=problem.problem.code, points=scoring[problem.id][0],
                         time=scoring[problem.id][1] - participation.start,
                         state=best_solution_state(scoring[problem.id][0], problem.points),
                         is_pretested=problem.is_pretested)
        if problem.id in scoring else None for problem in problems
    ])


def get_contest_ranking_list(request, contest, participation=None, ranking_list=contest_ranking_list,
                             show_current_virtual=True, ranker=ranker):
    problems = list(contest.contest_problems.select_related('problem').defer('problem__description').order_by('order'))

    if contest.hide_scoreboard and contest.is_in_contest(request):
        return [(_('???'), get_participation_ranking_profile(contest,
                                                             request.user.profile.current_contest, problems))], problems

    users = ranker(ranking_list(contest, problems), key=attrgetter('points', 'cumtime'))

    if show_current_virtual:
        if participation is None and request.user.is_authenticated:
            participation = request.user.profile.current_contest
            if participation is None or participation.contest_id != contest.id:
                participation = None
        if participation is not None and participation.virtual:
            users = chain([('-', get_participation_ranking_profile(contest, participation, problems))], users)
    return users, problems


def contest_ranking_ajax(request, contest, participation=None):
    contest, exists = _find_contest(request, contest)
    if not exists:
        return HttpResponseBadRequest('Invalid contest', content_type='text/plain')

    users, problems = get_contest_ranking_list(request, contest, participation)
    return render(request, 'contest/ranking-table.html', {
        'users': users,
        'problems': problems,
        'contest': contest,
        'has_rating': contest.ratings.exists(),
    })


def contest_ranking_view(request, contest, participation=None):
    if not contest.can_see_scoreboard(request):
        raise Http404()
    users, problems = get_contest_ranking_list(request, contest, participation)

    context = {
        'users': users,
        'title': _('%s Rankings') % contest.name,
        'content_title': contest.name,
        'problems': problems,
        'contest': contest,
        'last_msg': event.last(),
        'has_rating': contest.ratings.exists(),
        'tab': 'ranking',
    }

    # TODO: use ContestMixin when this becomes a class-based view
    if request.user.is_authenticated:
        profile = request.user.profile
        in_contest = context['in_contest'] = (profile.current_contest is not None and
                                              profile.current_contest.contest == contest)
        if in_contest:
            context['participation'] = profile.current_contest
            context['participating'] = True
        else:
            try:
                context['participation'] = profile.contest_history.get(contest=contest, virtual=0)
            except ContestParticipation.DoesNotExist:
                context['participating'] = False
                context['participation'] = None
            else:
                context['participating'] = True
    else:
        context['participating'] = False
        context['participation'] = None
        context['in_contest'] = False
    context['now'] = timezone.now()

    return render(request, 'contest/ranking.html', context)


def contest_ranking(request, contest):
    contest, exists = _find_contest(request, contest)
    if not exists:
        return contest
    return contest_ranking_view(request, contest)


def base_participation_list(request, contest, profile):
    contest, exists = _find_contest(request, contest)
    if not exists:
        return contest
    if not contest.can_see_scoreboard(request):
        raise Http404()

    req_username = request.user.username if request.user.is_authenticated else None
    prof_username = profile.user.username

    queryset = contest.users.filter(user=profile, virtual__gte=0).order_by('-virtual')
    live_link = format_html(u'<a href="{2}#!{1}">{0}</a>', _('Live'), prof_username,
                            reverse('contest_ranking', args=[contest.key]))
    users, problems = get_contest_ranking_list(
        request, contest, show_current_virtual=False,
        ranking_list=partial(base_contest_ranking_list, for_user=profile.id, queryset=queryset),
        ranker=lambda users, key: ((user.participation.virtual or live_link, user) for user in users))
    return render(request, 'contest/ranking.html', {
        'users': users,
        'title': _('Your participation in %s') % contest.name if req_username == prof_username else
        _("%s's participation in %s") % (prof_username, contest.name),
        'content_title': contest.name,
        # 'subtitle': _('Your participation') if req_username == prof_username else _(
        #    "%s's participation") % prof_username,
        'problems': problems,
        'contest': contest,
        'last_msg': event.last(),
        'has_rating': False,
        'now': timezone.now(),
        'rank_header': _('Participation'),
        'tab': 'participation',
    })


@login_required
def own_participation_list(request, contest):
    return base_participation_list(request, contest, request.user.profile)


def participation_list(request, contest, user):
    return base_participation_list(request, contest, get_object_or_404(Profile, user__username=user))


class ContestTagDetailAjax(DetailView):
    model = ContestTag
    slug_field = slug_url_kwarg = 'name'
    context_object_name = 'tag'
    template_name = 'contest/tag-ajax.html'


class ContestTagDetail(TitleMixin, ContestTagDetailAjax):
    template_name = 'contest/tag.html'

    def get_title(self):
        return _('Contest tag: %s') % self.object.name
