from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.comments import comment_form, contest_comments
from judge.models import Contest, ContestParticipation

__all__ = ['contest_list', 'contest', 'contest_ranking', 'join_contest']


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
    try:
        contest = Contest.objects.get(key=key)
        if not contest.is_public and not request.user.has_perm('judge.see_private_contest'):
            raise ObjectDoesNotExist()
        form = comment_form(request, 'c:' + key)
        if form is None:
            return HttpResponseRedirect(request.path)
        return render_to_response('contest.jade', {'contest': contest,
                                                   'title': contest.name,
                                                   'comment_list': contest_comments(contest),
                                                   'comment_form': form},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return render_to_response('message.jade', {'message': 'Could not find a contest with the key "%s".' % key,
                                                   'title': 'No such contest'},
                                  context_instance=RequestContext(request))


@login_required
def join_contest(request, key):
    try:
        contest = Contest.objects.get(key=key)
        if not contest.is_public and not request.user.has_perm('judge.see_private_contest'):
            raise ObjectDoesNotExist()
    except ObjectDoesNotExist:
        return render_to_response('message.jade', {
            'message': 'Could not find a contest with the key "%s".' % key,
            'title': 'No such contest'
        }, context_instance=RequestContext(request))

    contest_profile = request.user.profile.contest
    if contest_profile.current is not None:
        return render_to_response('message.jade', {
            'message': 'You are already in a contest: "%s".' % contest_profile.current.contest.name,
            'title': 'Already in contest'
        }, context_instance=RequestContext(request))
    if contest in contest_profile.history.all():
        return render_to_response('message.jade', {
            'message': 'You are already participated in the contest "%s".' % contest.name,
            'title': 'Already in contest'
        }, context_instance=RequestContext(request))
    participation = ContestParticipation()
    participation.contest = contest
    participation.profile = contest_profile
    participation.save()
    contest_profile.current = participation
    contest_profile.save()
    return HttpResponseRedirect(reverse('judge.views.contest', args=(key,)))


def contest_ranking(request, key):
    raise Http404()
