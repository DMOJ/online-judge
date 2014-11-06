from collections import namedtuple
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.functional import SimpleLazyObject
from judge.comments import comment_form, contest_comments
from judge.models import Contest, ContestParticipation
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


def contest_ranking_view(request, contest):
    results = [ContestRankingProfile(
        id=participation.profile.user_id,
        user=SimpleLazyObject(lambda: participation.profile.user.user),
        display_rank=SimpleLazyObject(lambda: participation.profile.user.display_rank),
        long_display_name=SimpleLazyObject(lambda: participation.profile.user.long_display_name),
        points=participation.score,
        problems=participation.submissions.values('problem').distinct().count()
    ) for participation in contest.users.order_by('-score')]
    return render_to_response('users.jade', {
        'users': ranker(results),
        'title': 'Ranking: %s' % contest.name
    }, context_instance=RequestContext(request))


def contest_ranking(request, key):
    contest, exists = _find_contest(request, key)
    if not exists:
        return contest
    return contest_ranking_view(request, contest)

