from collections import namedtuple
from operator import attrgetter
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Max
from django.http import HttpResponseRedirect, HttpResponseBadRequest, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import timezone
from django.utils.functional import SimpleLazyObject
from django.views.generic import ListView

from judge.comments import CommentedDetailView
from judge.models import Contest, ContestParticipation, ContestProblem, Profile
from judge.utils.ranker import ranker
from judge.utils.views import TitleMixin, generic_message
from judge import event_poster as event


__all__ = ['ContestList', 'ContestDetail', 'contest_ranking', 'join_contest', 'leave_contest', 'contest_ranking_ajax']


def _find_contest(request, key, private_check=True):
    try:
        contest = Contest.objects.get(key=key)
        if private_check and not contest.is_public and not request.user.has_perm('judge.see_private_contest'):
            raise ObjectDoesNotExist()
    except ObjectDoesNotExist:
        return render_to_response('generic_message.jade', {
            'message': 'Could not find a contest with the key "%s".' % key,
            'title': 'No such contest'
        }, context_instance=RequestContext(request)), False
    return contest, True


class ContestList(TitleMixin, ListView):
    model = Contest
    template_name = 'contest/list.jade'
    title = 'Contests'

    def get_queryset(self):
        if self.request.user.has_perm('judge.see_private_contest'):
            return Contest.objects.order_by('key')
        else:
            return Contest.objects.filter(is_public=True).order_by('key')

    def get_context_data(self, **kwargs):
        context = super(ContestList, self).get_context_data(**kwargs)
        now = timezone.now()
        past, present, future = [], [], []
        for contest in self.get_queryset():
            if contest.start_time is None:
                (present if contest.ongoing else past).append(contest)
            elif contest.end_time < now:
                past.append(contest)
            elif contest.start_time > now:
                future.append(contest)
            else:
                present.append(contest)
        context['current_contests'] = present
        context['past_contests'] = past
        context['future_contests'] = future
        return context


class ContestMixin(object):
    context_object_name = 'contest'
    model = Contest
    slug_field = 'key'
    slug_url_kwarg = 'key'
    private_check = True

    def get_object(self, queryset=None):
        contest = super(ContestMixin, self).get_object(queryset)
        if self.private_check and not contest.is_public and not self.request.user.has_perm('judge.see_private_contest'):
            raise Http404()

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(ContestMixin, self).dispatch(request, *args, **kwargs)
        except Http404:
            key = kwargs.get(self.slug_url_kwarg, None)
            if key:
                return generic_message(request, 'No such contest',
                                       'Could not find a contest with the key "%s".' % key)
            else:
                return generic_message(request, 'No such contest',
                                       'Could not find such contest.')


class ContestDetail(ContestMixin, TitleMixin, CommentedDetailView):
    template_name = 'contest/contest.jade'

    def get_comment_page(self):
        return 'c:%s' % self.object.key

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super(ContestDetail, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated():
            contest_profile = self.request.user.profile.contest
            try:
                context['participating'] = contest_profile.history.get(contest=contest)
            except ContestParticipation.DoesNotExist:
                context['participating'] = False
                context['participating'] = None
            else:
                context['participating'] = True
            context['in_contest'] = contest_profile.current is not None and contest_profile.current.contest == contest
        else:
            context['participating'] = False
            context['participating'] = None
            context['in_contest'] = False
        context['now'] = timezone.now()
        return context


@login_required
def join_contest(request, key):
    contest, exists = _find_contest(request, key)
    if not exists:
        return contest

    if not contest.can_join:
        return render_to_response('generic_message.jade', {
            'message': '"%s" is not currently ongoing.' % contest.name,
            'title': 'Contest not ongoing'
        }, context_instance=RequestContext(request))

    contest_profile = request.user.profile.contest
    if contest_profile.current is not None:
        return render_to_response('generic_message.jade', {
            'message': 'You are already in a contest: "%s".' % contest_profile.current.contest.name,
            'title': 'Already in contest'
        }, context_instance=RequestContext(request))

    participation, created = ContestParticipation.objects.get_or_create(
        contest=contest, profile=contest_profile, defaults={
            'start': contest.start_time or timezone.now()
        }
    )
    if not created and participation.ended:
        return render_to_response('generic_message.jade', {
            'message': 'Too late! You already used up your time limit for "%s".' % contest.name,
            'title': 'Time limit exceeded'
        }, context_instance=RequestContext(request))

    contest_profile.current = participation
    contest_profile.save()
    return HttpResponseRedirect(reverse('problem_list'))


@login_required
def leave_contest(request, key):
    # No public checking because if we hide the contest people should still be able to leave.
    # No lock ins.
    contest, exists = _find_contest(request, key, False)
    if not exists:
        return contest

    contest_profile = request.user.profile.contest
    if contest_profile.current is None or contest_profile.current.contest != contest:
        return render_to_response('generic_message.jade', {
            'message': 'You are not in contest "%s".' % key,
            'title': 'No such contest'
        }, context_instance=RequestContext(request))
    contest_profile.current = None
    contest_profile.save()
    return HttpResponseRedirect(reverse('judge.views.contest', args=(key,)))


ContestRankingProfile = namedtuple('ContestRankingProfile',
                                   'id user display_rank long_display_name points cumtime problems organization')
BestSolutionData = namedtuple('BestSolutionData', 'code points time state')


def get_best_contest_solutions(problems, profile, participation):
    solutions = []
    assert isinstance(profile, Profile)
    assert isinstance(participation, ContestParticipation)
    for problem in problems:
        assert isinstance(problem, ContestProblem)
        queryset = problem.submissions.filter(submission__user_id=profile.id).values('submission__user_id')
        solution = queryset.annotate(best=Max('points'))
        if not solution:
            solutions.append(None)
            continue
        time = queryset.filter(points__gt=0).annotate(time=Max('submission__date'))
        best = solution[0]['best']
        solutions.append(BestSolutionData(
            code=problem.problem.code,
            points=best,
            time=time[0]['time'] - participation.start if time else timedelta(seconds=0),
            state='failed-score' if not best else
                  ('full-score' if best == problem.points else 'partial-score'),
        ))
    return solutions


def contest_ranking_list(contest, problems):
    assert isinstance(contest, Contest)

    def make_ranking_profile(participation):
        contest_profile = participation.profile
        return ContestRankingProfile(
            id=contest_profile.user_id,
            user=SimpleLazyObject(lambda: contest_profile.user.user),
            display_rank=SimpleLazyObject(lambda: contest_profile.user.display_rank),
            long_display_name=SimpleLazyObject(lambda: contest_profile.user.long_display_name),
            points=participation.score,
            cumtime=participation.cumtime,
            organization=SimpleLazyObject(lambda: contest_profile.user.organization),
            problems=SimpleLazyObject(lambda: get_best_contest_solutions(problems, contest_profile.user, participation))
        )

    return map(make_ranking_profile, contest.users.select_related('profile').order_by('-score', 'cumtime'))


def contest_ranking_ajax(request, key):
    contest, exists = _find_contest(request, key)
    if not exists:
        return HttpResponseBadRequest('Invalid contest', content_type='text/plain')
    problems = list(contest.contest_problems.select_related('problem').defer('problem__description'))
    return render_to_response('contest/ranking_table.jade', {
        'users': ranker(contest_ranking_list(contest, problems), key=attrgetter('points', 'cumtime')),
        'problems': problems,
        'contest': contest,
        'show_organization': True,
    }, context_instance=RequestContext(request))


def contest_ranking_view(request, contest):
    problems = list(contest.contest_problems.select_related('problem').defer('problem__description'))
    return render_to_response('contest/ranking.jade', {
        'users': ranker(contest_ranking_list(contest, problems), key=attrgetter('points', 'cumtime')),
        'title': '%s Rankings' % contest.name,
        'content_title': contest.name,
        'subtitle': 'Rankings',
        'problems': problems,
        'contest': contest,
        'show_organization': True,
        'last_msg': event.last(),
    }, context_instance=RequestContext(request))


def contest_ranking(request, key):
    contest, exists = _find_contest(request, key)
    if not exists:
        return contest
    return contest_ranking_view(request, contest)
