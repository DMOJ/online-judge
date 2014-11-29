import logging
from operator import attrgetter
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import Http404, HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.generic import ListView, View, UpdateView, CreateView
from django.views.generic.detail import SingleObjectMixin

from judge.comments import CommentedDetailView
from judge.forms import ProblemSubmitForm, ProblemEditForm, ProblemAddForm
from judge.models import Problem, Submission, ContestSubmission, ContestProblem, Language, ContestProfile
from judge.pdf_problems import make_latex, format_markdown, latex_document, LatexPdfMaker
from judge.utils.problems import contest_completed_ids, user_completed_ids
from judge.utils.views import TitleMixin, generic_message


def get_contest_problem(problem, profile):
    try:
        return problem.contests.get(contest=profile.contest.current.contest)
    except ObjectDoesNotExist:
        return None


class ProblemMixin(object):
    model = Problem
    slug_url_kwarg = slug_field = 'code'

    def get_object(self, queryset=None):
        problem = super(ProblemMixin, self).get_object(queryset)
        if not problem.is_public and not self.request.user.has_perm('judge.see_private_problem'):
            if self.request.user.has_perm('judge.edit_own_problem') and \
                    problem.authors.filter(id=self.request.user.profile.id).exists():
                return problem

            if self.request.user.is_authenticated():
                cp = self.request.user.profile.contest
                assert isinstance(cp, ContestProfile)
                if cp.current is None or not cp.current.contest.problems.filter(id=problem.id).exists():
                    raise Http404()
            else:
                raise Http404()
        return problem

    def get(self, request, *args, **kwargs):
        try:
            return super(ProblemMixin, self).get(request, *args, **kwargs)
        except Http404:
            code = kwargs.get(self.slug_url_kwarg, None)
            return generic_message(request, 'No such problem', 'Could not find a problem with the code "%s".' % code)


class ProblemDetail(ProblemMixin, TitleMixin, CommentedDetailView):
    context_object_name = 'problem'
    template_name = 'problem/problem.jade'

    def get_comment_page(self):
        return 'p:%s' % self.object.code

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super(ProblemDetail, self).get_context_data(**kwargs)
        user = self.request.user
        authed = user.is_authenticated()
        context['has_submissions'] = authed and Submission.objects.filter(user=user.profile).exists()
        context['contest_problem'] = (None if not authed or user.profile.contest.current is None else
                                      get_contest_problem(self.object, user.profile))
        context['show_languages'] = self.object.allowed_languages.count() != Language.objects.count()
        return context


class ProblemEdit(ProblemMixin, TitleMixin, UpdateView):
    template_name = 'problem/edit.jade'
    form_class = ProblemEditForm

    def get_title(self):
        return 'Editing %s' % self.object.name

    def get_object(self, queryset=None):
        problem = super(ProblemEdit, self).get_object()
        if not self.request.user.has_perm('judge.edit_own_problem'):
            raise PermissionDenied()
        if not problem.authors.filter(id=self.request.user.profile.id).exists():
            raise PermissionDenied()
        return problem

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(ProblemEdit, self).dispatch(request, *args, **kwargs)
        except PermissionDenied:
            return generic_message(request, "Can't edit problem",
                                   'You are not allowed to edit this problem.')


class ProblemCreate(ProblemMixin, TitleMixin, CreateView):
    template_name = 'problem/edit.jade'
    form_class = ProblemAddForm
    title = 'Adding new problem'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('judge.change_problem') and not request.user.has_perm('judge.edit_own_problem'):
            raise PermissionDenied()
        return super(ProblemCreate, self).dispatch(request, *args, **kwargs)


class LatexError(Exception):
    pass


class ProblemLatexView(ProblemMixin, SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        if not request.user.has_perm('judge.change_problem'):
            raise Http404()
        problem = self.get_object()
        authors = ', '.join(map(attrgetter('user.username'), problem.authors.select_related('user')))
        document = latex_document(problem.name, authors, make_latex(format_markdown(problem.description)))
        return HttpResponse(document, content_type='text/plain')


class ProblemPdfView(ProblemMixin, SingleObjectMixin, View):
    logger = logging.getLogger('judge.problem.pdf')

    def get(self, request, *args, **kwargs):
        if not hasattr(settings, 'PROBLEM_PDF_CACHE'):
            raise Http404()

        problem = self.get_object()
        error_cache = os.path.join(settings.PROBLEM_PDF_CACHE, '%s.log' % problem.code)
        cache = os.path.join(settings.PROBLEM_PDF_CACHE, '%s.pdf' % problem.code)

        if os.path.exists(error_cache):
            with open(error_cache) as f:
                return HttpResponse(f.read(), status=500, content_type='text/plain')

        if not os.path.exists(cache):
            self.logger.info('Rendering: %s.pdf', problem.code)
            try:
                authors = ', '.join(map(attrgetter('user.username'), problem.authors.select_related('user')))
                document = latex_document(problem.name, authors, make_latex(format_markdown(problem.description)))
                with LatexPdfMaker(document) as latex:
                    latex.make()
                    if not latex.success:
                        # try:
                        #     raise LatexError(latex.log)
                        # except LatexError:
                        #     self.logger.exception('Latex error while rendering: %s.pdf', problem.code)
                        if not latex.created:
                            with open(error_cache, 'wb') as f:
                                f.write(latex.log)
                            return HttpResponse(latex.log, status=500, content_type='text/plain')
                    os.rename(latex.pdffile, cache)
            except:
                self.logger.exception('Error while rendering: %s.pdf', problem.code)
                raise
            else:
                self.logger.info('Successfully rendered: %s.pdf', problem.code)

        #if hasattr(settings, 'PROBLEM_PDF_INTERNAL') and request.META.get('SERVER_SOFTWARE', '').startswith('nginx/'):
        #    response = HttpResponse()
        #    response['X-Accel-Redirect'] = '/%s/%s.pdf' % (settings.PROBLEM_PDF_INTERNAL, problem.code)
        #else:
        with open(cache, 'rb') as f:
            response = HttpResponse(f.read())

        response['Content-Type'] = 'application/pdf'
        response['Content-Disposition'] = 'inline; filename=%s.pdf' % problem.code
        return response


class ProblemList(TitleMixin, ListView):
    model = Problem
    title = 'Problems'
    context_object_name = 'problems'
    template_name = 'problem/list.jade'

    @cached_property
    def profile(self):
        if not self.request.user.is_authenticated():
            return None
        return self.request.user.profile

    @cached_property
    def contest_profile(self):
        return self.profile and self.profile.contest

    @cached_property
    def in_contest(self):
        return self.contest_profile is not None and self.contest_profile.current is not None

    def get_contest_queryset(self):
        queryset = self.contest_profile.current.contest.contest_problems.select_related('problem__group') \
                       .defer('problem__description').order_by('problem__code') \
                       .annotate(number_of_users=Count('submission__participation', distinct=True))
        return [{
            'id': p.problem.id,
            'code': p.problem.code,
            'name': p.problem.name,
            'group': p.problem.group,
            'points': p.points,
            'partial': p.partial,
            'number_of_users': p.number_of_users
        } for p in queryset]

    def get_normal_queryset(self):
        queryset = Problem.objects.filter(is_public=True) \
                          .annotate(number_of_users=Count('submission__user', distinct=True))\
                          .select_related('group').defer('description').order_by('code')
        if self.hide_solved:
            queryset = queryset.exclude(id__in=Submission.objects.filter(user=self.profile, result='AC')
                               .values_list('problem__id', flat=True))
        return queryset

    def get_queryset(self):
        if self.in_contest:
            return self.get_contest_queryset()
        else:
            return self.get_normal_queryset()

    def get_completed_problems(self):
        if self.in_contest:
            return contest_completed_ids(self.contest_profile.current)
        else:
            return user_completed_ids(self.profile) if self.profile is not None else ()

    def get_context_data(self, **kwargs):
        context = super(ProblemList, self).get_context_data(**kwargs)
        context['hide_solved'] = int(self.hide_solved)
        context['completed_problem_ids'] = self.get_completed_problems()
        return context

    def get(self, request, *args, **kwargs):
        self.hide_solved = request.GET.get('hide_solved') == '1' if 'hide_solved' in request.GET else False
        return super(ProblemList, self).get(request, *args, **kwargs)


class OwnProblemList(TitleMixin, ListView):
    title = 'My Problems'
    context_object_name = 'problems'
    template_name = 'problem/own_list.jade'

    def get_queryset(self):
        return Problem.objects.filter(authors__id=self.request.user.profile.id) \
                      .annotate(number_of_users=Count('submission__user', distinct=True))\
                      .select_related('group').defer('description').order_by('code')

    def get_context_data(self, **kwargs):
        context = super(OwnProblemList, self).get_context_data(**kwargs)
        context['completed_problem_ids'] = user_completed_ids(self.request.user.profile)
        return context

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('judge.change_problem') and not request.user.has_perm('judge.edit_own_problem'):
            raise PermissionDenied()
        return super(OwnProblemList, self).dispatch(request, *args, **kwargs)


@login_required
def problem_submit(request, problem=None, submission=None):
    try:
        if submission is not None and Submission.objects.get(id=int(submission)).user.user != request.user:
            raise PermissionDenied()
    except Submission.DoesNotExist:
        raise Http404()

    if request.method == 'POST':
        form = ProblemSubmitForm(request.POST, instance=Submission(user=request.user.profile))
        if form.is_valid():
            if (not request.user.has_perm('judge.spam_submission') and
                        Submission.objects.filter(user=request.user.profile).exclude(
                                status__in=['D', 'IE', 'CE', 'AB']).count() > 2):
                return HttpResponse('<h1>You submitted too many submissions.</h1>', status=503)
            if not form.cleaned_data['problem'].allowed_languages.filter(
                    id=form.cleaned_data['language'].id).exists():
                raise PermissionDenied()
            model = form.save()

            cp = request.user.profile.contest
            if cp.current is not None:
                try:
                    contest_problem = model.problem.contests.get(contest=cp.current.contest)
                except ContestProblem.DoesNotExist:
                    pass
                else:
                    contest = ContestSubmission(submission=model, problem=contest_problem,
                                                participation=cp.current)
                    contest.save()

            model.judge()
            return HttpResponseRedirect(reverse('submission_status', args=[str(model.id)]))
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
    return render_to_response('problem/submit.jade', {
        'form': form,
        'title': 'Submit',
        'langs': Language.objects.all(),
    }, context_instance=RequestContext(request))
