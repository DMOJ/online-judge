import itertools
import logging
import os
from operator import attrgetter
from random import randrange

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db.models import Count, Q, F
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.template import Context
from django.template.loader import get_template
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _, ugettext_lazy as __
from django.views.generic import ListView, View
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin

from judge.comments import CommentedDetailView
from judge.forms import ProblemSubmitForm
from judge.models import Problem, Submission, ContestSubmission, ContestProblem, Language, ProblemGroup, Solution
from judge.pdf_problems import make_latex, format_markdown, latex_document, LatexPdfMaker, WebKitPdfMaker
from judge.utils.problems import contest_completed_ids, user_completed_ids
from judge.utils.views import TitleMixin, generic_message


def get_contest_problem(problem, profile):
    try:
        return problem.contests.get(contest=profile.contest.current.contest)
    except ObjectDoesNotExist:
        return None


class ProblemMixin(object):
    model = Problem
    slug_url_kwarg = 'problem'
    slug_field = 'code'

    def get_object(self, queryset=None):
        problem = super(ProblemMixin, self).get_object(queryset)
        if not problem.is_public and not self.request.user.has_perm('judge.see_private_problem'):
            if self.request.user.has_perm('judge.edit_own_problem') and \
                    problem.authors.filter(id=self.request.user.profile.id).exists():
                return problem

            if self.request.user.is_authenticated():
                cp = self.request.user.profile.contest
                if not Problem.objects.filter(id=problem.id, contest__users__profile=cp).exists():
                    raise Http404()
            else:
                raise Http404()
        return problem

    def get(self, request, *args, **kwargs):
        try:
            return super(ProblemMixin, self).get(request, *args, **kwargs)
        except Http404:
            code = kwargs.get(self.slug_url_kwarg, None)
            return generic_message(request, _('No such problem'),
                                   _('Could not find a problem with the code "%s".') % code, status=404)


class ProblemRaw(ProblemMixin, TitleMixin, TemplateResponseMixin, SingleObjectMixin, View):
    context_object_name = 'problem'
    template_name = 'problem/raw.jade'

    def get_title(self):
        return self.get_object().name

    def get_context_data(self, **kwargs):
        context = super(ProblemRaw, self).get_context_data(**kwargs)
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data(
            object=self.object,
        ))


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
        context['wkhtmltopdf_installed'] = getattr(settings, 'WEBKIT_PDF', False)
        try:
            context['editorial'] = Solution.objects.get(problem=self.object)
        except ObjectDoesNotExist:
            pass
        return context


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
            if getattr(settings, 'WEBKIT_PDF', False):
                with WebKitPdfMaker() as maker:
                    maker.html = get_template('problem/raw.jade').render(Context({
                        'problem': problem
                    })).replace('"//', '"http://').replace("'//", "'http://")
                    for file in ('style.css', 'pygment-github.css'):
                        maker.load(file, os.path.join(settings.DMOJ_RESOURCES, file))
                    maker.make()
                    if not maker.success:
                        with open(error_cache, 'wb') as f:
                            f.write(maker.log)
                        return HttpResponse(maker.log, status=500, content_type='text/plain')
                    os.rename(maker.pdffile, cache)
            else:
                try:
                    authors = ', '.join(map(attrgetter('user.username'), problem.authors.select_related('user')))
                    document = latex_document(problem.name, authors, make_latex(format_markdown(problem.description)))
                    with LatexPdfMaker(document) as latex:
                        latex.make()
                        if not latex.success:
                            # try:
                            # raise LatexError(latex.log)
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

        response = HttpResponse()
        if hasattr(settings, 'PROBLEM_PDF_INTERNAL') and request.META.get('SERVER_SOFTWARE', '').startswith('nginx/'):
            response['X-Accel-Redirect'] = '%s/%s.pdf' % (settings.PROBLEM_PDF_INTERNAL, problem.code)
        else:
            with open(cache, 'rb') as f:
                response.content = f.read()

        response['Content-Type'] = 'application/pdf'
        response['Content-Disposition'] = 'inline; filename=%s.pdf' % problem.code
        return response


class ProblemList(TitleMixin, ListView):
    model = Problem
    title = __('Problems')
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
            .annotate(number_of_users=Count('submission__participation', distinct=True)) \
            .order_by('order')
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
        filter = Q(is_public=True)
        if self.profile is not None:
            filter |= Q(id__in=Problem.objects.filter(contest__users__profile=self.profile.contest)
                                      .values('id').distinct())
            filter |= Q(authors=self.profile)
        queryset = Problem.objects.filter(filter) \
            .annotate(number_of_users=Count('submission__user', distinct=True)) \
            .select_related('group').defer('description').order_by('code')
        if self.profile is not None and self.hide_solved:
            queryset = queryset.exclude(id__in=Submission.objects.filter(user=self.profile, points=F('problem__points'))
                                        .values_list('problem__id', flat=True))
        if self.show_types:
            queryset = queryset.prefetch_related('types')
        if self.category is not None:
            queryset = queryset.filter(group_id=self.category)
        if settings.ENABLE_FTS and 'search' in self.request.GET:
            self.search_query = query = ' '.join(self.request.GET.getlist('search')).strip()
            if query:
                queryset = queryset.search(query)
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
        context['show_types'] = int(self.show_types)
        context['category'] = self.category
        context['categories'] = ProblemGroup.objects.all()
        context['has_search'] = settings.ENABLE_FTS
        context['search_query'] = self.search_query
        context['completed_problem_ids'] = self.get_completed_problems()
        return context

    def get(self, request, *args, **kwargs):
        self.hide_solved = request.GET.get('hide_solved') == '1' if 'hide_solved' in request.GET else False
        self.show_types = request.GET.get('show_types') == '1' if 'show_types' in request.GET else False
        self.search_query = None
        self.category = None
        if 'category' in request.GET:
            try:
                self.category = int(request.GET.get('category'))
            except ValueError:
                pass
        return super(ProblemList, self).get(request, *args, **kwargs)


@login_required
def problem_submit(request, problem=None, submission=None):
    try:
        if submission is not None and not request.user.has_perm('judge.resubmit_other') and \
                Submission.objects.get(id=int(submission)).user.user != request.user:
            raise PermissionDenied()
    except Submission.DoesNotExist:
        raise Http404()

    profile = request.user.profile
    if request.method == 'POST':
        form = ProblemSubmitForm(request.POST, instance=Submission(user=profile))
        if form.is_valid():
            if (not request.user.has_perm('judge.spam_submission') and
                        Submission.objects.filter(user=profile).exclude(
                                status__in=['D', 'IE', 'CE', 'AB']).count() > 2):
                return HttpResponse('<h1>You submitted too many submissions.</h1>', status=503)
            if not form.cleaned_data['problem'].allowed_languages.filter(
                    id=form.cleaned_data['language'].id).exists():
                raise PermissionDenied()
            if not request.user.is_superuser and form.cleaned_data['problem'].banned_users.filter(id=profile.id).exists():
                return generic_message(request, _('Banned from Submitting'),
                                       _('You have been declared persona non grata for this problem. '
                                         'You are permanently barred from submitting this problem.'))
            model = form.save()

            cp = profile.contest
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
        initial = {'language': profile.language}
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
        form.fields['language'].queryset = form_data['problem'].usable_languages
    if 'language' in form_data:
        form.fields['source'].widget.mode = form_data['language'].ace
    form.fields['source'].widget.theme = profile.ace_theme
    return render(request, 'problem/submit.jade', {
        'form': form,
        'title': _('Submit'),
        'langs': Language.objects.all(),
        'no_judges': not form.fields['language'].queryset
    })


@login_required
@permission_required('judge.clone_problem')
def clone_problem(request, problem):
    problem = get_object_or_404(Problem, code=problem)
    languages = problem.allowed_languages.all()
    problem.pk = None
    problem.is_public = False
    problem.code += '_clone'
    try:
        problem.save()
    except IntegrityError:
        code = problem.code
        for i in itertools.count(1):
            problem.code = '%s%d' % (code, i)
            try:
                problem.save()
            except IntegrityError:
                pass
            else:
                break
    problem.authors.add(request.user.profile)
    problem.allowed_languages = languages
    return HttpResponseRedirect(reverse('admin:judge_problem_change', args=(problem.id,)))


def random_problem(request):
    count = Problem.objects.filter(is_public=True).aggregate(count=Count('id'))['count']
    return HttpResponseRedirect(Problem.objects.filter(is_public=True)[randrange(count)].get_absolute_url())
