from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from judge.comments import problem_comments, comment_form
from judge.forms import ProblemSubmitForm
from judge.models import Problem, Submission


def get_result_table(**kwargs):
    results = {}
    submissions = Submission.objects.filter(**kwargs) if kwargs is not None else Submission.objects
    for code in ['AC', 'WA', 'TLE', 'IR', 'MLE']:
        results[code] = submissions.filter(result=code).count()
    results['CE'] = submissions.filter(status='CE').count()
    return [('Accepted', 'AC', results['AC']),
            ('Wrong Answer', 'WA', results['WA']),
            ('Compile Error', 'CE', results['CE']),
            ('Time Limit Exceed', 'TLE', results['TLE']),
            ('Memory Limit Exceed', 'MLE', results['MLE']),
            ('Invalid Return', 'IR', results['IR']),
            ('Total', 'TOT', sum(results.values()))]


def problem(request, code):
    try:
        problem = Problem.objects.get(code=code)
        form = comment_form(request, 'p:' + code)
        if form is None:
            return HttpResponseRedirect(request.path)
        return render_to_response('problem.jade', {'problem': problem, 'results': get_result_table(problem__code=code),
                                                   'title': 'Problem: %s' % problem.name,
                                                   'has_submissions': request.user.is_authenticated() and Submission.objects.filter(
                                                       user=request.user.profile).exists(),
                                                   'comment_list': problem_comments(problem),
                                                   'comment_form': form},
                                  context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        raise Http404()


def problems(request):
    hide_solved = request.GET.get('hide_solved') == '1' if 'hide_solved' in request.GET else False

    if hide_solved and request.user.is_authenticated:
        probs = Problem.unsolved(request.user.profile)
    else:
        probs = Problem.objects
    probs = probs.order_by('code')
    return render_to_response('problems.jade', {
        'problems': probs,
        'hide_solved': 1 if hide_solved else 0,
        'title': 'Problems'}, context_instance=RequestContext(request))


@login_required
def problem_submit(request, problem=None, submission=None):
    if request.method == 'POST':
        form = ProblemSubmitForm(request.POST, instance=Submission(user=request.user.profile))
        if form.is_valid():
            if (not request.user.has_perm('judge.spam_submission') and
                        Submission.objects.filter(user=request.user.profile).exclude(
                                status__in=['D', 'IE', 'CE']).count() > 2):
                return HttpResponse('<h1>You submitted too many submissions.</h1>', status=503)
            if not form.cleaned_data['problem'].allowed_languages.filter(id=form.cleaned_data['language'].id).exists():
                raise PermissionDenied()
            model = form.save()
            model.judge()
            return HttpResponseRedirect(reverse('judge.views.submission_status', args=[str(model.id)]))
        else:
            form_data = form.cleaned_data
    else:
        initial = {'language': request.user.profile.language}
        if problem is not None:
            try:
                initial['problem'] = Problem.objects.get(code=problem)
            except ObjectDoesNotExist:
                raise Http404()
        if submission is not None:
            try:
                sub = Submission.objects.get(id=int(submission))
                initial['source'] = sub.source
                initial['language'] = sub.language
            except (ObjectDoesNotExist, ValueError):
                raise Http404()
        form = ProblemSubmitForm(initial=initial)
        form_data = initial
    if 'problem' in form_data:
        form.fields['language'].queryset = form_data['problem'].allowed_languages
    form.fields['source'].widget.mode = form_data['language'].ace
    form.fields['source'].widget.theme = request.user.profile.ace_theme
    return render_to_response('problem_submit.jade', {
        'form': form,
        'title': 'Submit',
        'langs': form.fields['language'].queryset.all(),
    }, context_instance=RequestContext(request))
