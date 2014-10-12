from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.comments import comment_form, contest_comments
from judge.models import Contest

__all__ = ['contest_list', 'contest', 'contest_ranking']


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
        contest = Contest.objects.get(code=key)
        if not contest.is_public and not request.user.has_perm('judge.see_private_contest'):
            raise ObjectDoesNotExist()
        form = comment_form(request, 'p:' + key)
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


def contest_ranking(request, key):
    return Http404()
