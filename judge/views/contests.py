from collections import namedtuple
from functools import partial
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Max
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.functional import SimpleLazyObject
from judge.comments import comment_form, contest_comments
from judge.models import Contest, ContestParticipation, ContestProblem, Profile
from judge.utils.ranker import ranker

__all__ = ['contest_list', 'contest', 'contest_ranking', 'join_contest', 'leave_contest']


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


def contest_list(request):
    if request.user.has_perm('judge.see_private_contest'):
        contests = Contest.objects.all()
    else:
        contests = Contest.objects.filter(is_public=True)
    return render_to_response('contests.jade', {
        'contests': contests,
        'title': 'Contests'
    }, context_instance=RequestContext(request))


def contest(request, key):
    contest, exists = _find_contest(request, key)
    if not exists:
        return contest

    form = comment_form(request, 'c:' + key)
    if form is None:
        return HttpResponseRedirect(request.path)

    if request.user.is_authenticated():
        contest_profile = request.user.profile.contest
        try:
            participation = contest_profile.history.get(contest=contest)
        except ContestParticipation.DoesNotExist:
            participating = False
            participation = None
        else:
            participating = True
        in_contest = contest_profile.current is not None and contest_profile.current.contest == contest
    else:
        participating = False
        participation = None
        in_contest = False
    return render_to_response('contest.jade', {
        'contest': contest,
        'title': contest.name,
        'comment_list': contest_comments(contest),
        'comment_form': form,
        'in_contest': in_contest,
        'participating': participating,
        'participation': participation,
    }, context_instance=RequestContext(request))


@login_required
def join_contest(request, key):
    contest, exists = _find_contest(request, key)
    if not exists:
        return contest

    contest_profile = request.user.profile.contest
    if contest_profile.current is not None:
        return render_to_response('generic_message.jade', {
            'message': 'You are already in a contest: "%s".' % contest_profile.current.contest.name,
            'title': 'Already in contest'
        }, context_instance=RequestContext(request))

    participation, created = ContestParticipation.objects.get_or_create(contest=contest, profile=contest_profile)
    if not created and participation.ended:
        return render_to_response('generic_message.jade', {
            'message': 'Too late! You already used up your time limit for "%s".' % contest.name,
            'title': 'Already in contest'
        }, context_instance=RequestContext(request))

    contest_profile.current = participation
    contest_profile.save()
    return HttpResponseRedirect(reverse('judge.views.contest', args=(key,)))


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
                                   'id user display_rank long_display_name points problems')
BestSolutionData = namedtuple('BestSolutionData', 'points time state')


def get_best_contest_solutions(problems, profile, participation):
    solutions = []
    assert isinstance(profile, Profile)
    assert isinstance(participation, ContestParticipation)
    for problem in problems:
        assert isinstance(problem, ContestProblem)
        solution = problem.submissions.filter(submission__user_id=profile.id).values('submission__user_id')\
            .annotate(best=Max('points'), time=Max('submission__date'))
        if not solution:
            solutions.append(None)
            continue
        solution = solution[0]
        solutions.append(BestSolutionData(
            points=solution['best'],
            time=solution['time'] - participation.start,
            state='failed-score' if not solution['best'] else
                  ('full-score' if solution['best'] == problem.points else 'partial-score'),
        ))
    return solutions


def contest_ranking_view(request, contest):
    assert isinstance(contest, Contest)
    problems = list(contest.contest_problems.all())

    def make_ranking_profile(participation):
        contest_profile = participation.profile
        return ContestRankingProfile(
            id=contest_profile.user_id,
            user=SimpleLazyObject(lambda: contest_profile.user.user),
            display_rank=SimpleLazyObject(lambda: contest_profile.user.display_rank),
            long_display_name=SimpleLazyObject(lambda: contest_profile.user.long_display_name),
            points=participation.score,
            problems=SimpleLazyObject(lambda: get_best_contest_solutions(problems, contest_profile.user, participation))
        )

    results = map(make_ranking_profile, contest.users.select_related('profile').order_by('-score'))
    return render_to_response('contest_ranking.jade', {
        'users': ranker(results),
        'title': 'Ranking: %s' % contest.name,
        'problems': problems
    }, context_instance=RequestContext(request))


def contest_ranking(request, key):
    contest, exists = _find_contest(request, key)
    if not exists:
        return contest
    return contest_ranking_view(request, contest)
